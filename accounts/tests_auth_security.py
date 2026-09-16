from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt
from axes.utils import reset
from captcha.models import CaptchaStore
import time

User = get_user_model()

class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        self.client = Client()
        self.user = User.objects.create_user(username="secuser@acme.test", email="secuser@acme.test", password="SecurePassword123!")
        reset()  # Reset any axes lockouts
        cache.clear() # Clear axes cache

    def test_account_enumeration_timing(self):
        # Time a valid user with wrong password
        start = time.time()
        self.client.post(reverse('login'), {'username': 'secuser@acme.test', 'password': 'wrongpassword'})
        duration_valid = time.time() - start
        
        # Time an invalid user with wrong password
        start = time.time()
        self.client.post(reverse('login'), {'username': 'invaliduser123@acme.test', 'password': 'wrongpassword'})
        duration_invalid = time.time() - start
        
        # The time difference should be negligible to prevent timing attacks
        # (Usually < 1.0s difference is acceptable for testing)
        self.assertLess(abs(duration_valid - duration_invalid), 1.0)
        
    def test_rate_limiting_and_adaptive_captcha(self):
        url = reverse('login')
        
        # Simulate 3 failed attempts
        for i in range(3):
            self.client.post(url, {'username': 'secuser@acme.test', 'password': f'wrong_{i}'})
        
        # 4th attempt (without captcha) should return the form with captcha field
        response = self.client.post(url, {'username': 'secuser@acme.test', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('captcha', response.context['form'].fields)

    def test_brute_force_prevention(self):
        # Uses django-axes for brute-force prevention
        url = reverse('login')
        # Fail 5 times (AXES_FAILURE_LIMIT=5)
        for i in range(5):
            captcha = CaptchaStore.generate_key()
            valid_response = CaptchaStore.objects.get(hashkey=captcha).response
            self.client.post(url, {
                'username': 'bruteforce@acme.test', 
                'password': f'wrong_{i}',
                'captcha_0': captcha,
                'captcha_1': valid_response,
            })
            
        # 6th attempt should be blocked
        captcha = CaptchaStore.generate_key()
        valid_response = CaptchaStore.objects.get(hashkey=captcha).response
        response = self.client.post(url, {
            'username': 'bruteforce@acme.test', 
            'password': 'any',
            'captcha_0': captcha,
            'captcha_1': valid_response,
        })
        self.assertEqual(response.status_code, 429)

    def test_hard_lockout_after_max_attempts(self):
        url = reverse('login')
        
        # Fail 5 times to hit AXES_FAILURE_LIMIT=5
        for i in range(5):
            captcha = CaptchaStore.generate_key()
            valid_response = CaptchaStore.objects.get(hashkey=captcha).response
            self.client.post(url, {
                'username': 'secuser@acme.test', 
                'password': f'wrong_{i}',
                'captcha_0': captcha,
                'captcha_1': valid_response,
            })

        # Attempt 6 should be locked out (Axes returns 429 by default with template)
        captcha = CaptchaStore.generate_key()
        valid_response = CaptchaStore.objects.get(hashkey=captcha).response
        response = self.client.post(url, {
            'username': 'secuser@acme.test', 
            'password': 'SecurePassword123!',
            'captcha_0': captcha,
            'captcha_1': valid_response,
        })
        self.assertEqual(response.status_code, 429)

    def test_logout_invalidates_session(self):
        self.client.force_login(self.user)
        session_key_before = self.client.session.session_key
        
        response = self.client.post(reverse('logout')) # assuming POST or GET depending on view
        if response.status_code == 405:
            response = self.client.get(reverse('logout'))
            
        self.assertNotEqual(self.client.session.session_key, session_key_before)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_csrf_protection_on_login(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('login'), {'username': 'secuser@acme.test', 'password': 'SecurePassword123!'})
        # Without CSRF token, should fail with 403
        self.assertEqual(response.status_code, 403)
