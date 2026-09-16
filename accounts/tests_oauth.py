from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from unittest.mock import patch, MagicMock
from authlib.integrations.django_client import OAuthError
from accounts.oauth import oauth

User = get_user_model()

class GoogleOAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="oauthuser@acme.test",
            email="oauthuser@acme.test",
            password="SecurePassword123!",
            is_active=True
        )
        # Create an employee profile so the user can login
        from employees.models import Employee
        from organizations.models import Organization
        from departments.models import Department
        from locations.models import Location
        from designations.models import Designation
        from rbac.models import Role
        
        org = Organization.objects.create(name="Test Org", code="ORG1")
        dept = Department.objects.create(name="Test Dept", code="DEPT1", organization=org)
        loc = Location.objects.create(name="Test Loc", code="LOC1", organization=org)
        desig = Designation.objects.create(name="Test Desig", code="DES1", organization=org)
        role = Role.objects.create(name="Test Role", code="ROLE1")
        
        self.employee = Employee.objects.create(
            user=self.user,
            organization=org,
            department=dept,
            location=loc,
            designation=desig,
            role=role,
            employee_code="EMP-OAUTH",
            joining_date="2020-01-01",
            is_active=True
        )

    def test_oauth_routes_reachable_anonymously(self):
        response = self.client.get(reverse('google_login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://accounts.google.com/'))

    def test_production_callback_uri_generation(self):
        # Without SECURE_PROXY_SSL_HEADER, a request forwarded by a proxy over HTTP
        # will generate an HTTP callback URI, which causes redirect_uri_mismatch if Google expects HTTPS.
        
        # Test HTTP request
        response = self.client.get(reverse('google_login'), HTTP_HOST='anukram.onrender.com')
        self.assertEqual(response.status_code, 302)
        self.assertIn('redirect_uri=http%3A%2F%2Fanukram.onrender.com%2Flogin%2Fgoogle%2Fcallback%2F', response.url)
        
        # Test with Render's X-Forwarded-Proto header (simulating the fix being applied)
        with self.settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')):
            response = self.client.get(reverse('google_login'), HTTP_HOST='anukram.onrender.com', HTTP_X_FORWARDED_PROTO='https')
            self.assertEqual(response.status_code, 302)
            self.assertIn('redirect_uri=https%3A%2F%2Fanukram.onrender.com%2Flogin%2Fgoogle%2Fcallback%2F', response.url)

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_google_login_success(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'oauthuser@acme.test',
                'email_verified': True
            }
        }
        
        # Mock authlib to skip state validation for this test
        with patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token', mock_access_token):
            response = self.client.get(reverse('google_callback'))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('dashboard'))

    @patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token')
    def test_invalid_or_missing_oauth_state(self, mock_access_token):
        # authlib raises MismatchingStateError if state is missing/invalid
        mock_access_token.side_effect = OAuthError('mismatching_state')
        
        response = self.client.get(reverse('google_callback') + '?state=invalid&code=abc')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to authenticate with Google")

    @patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token')
    def test_invalid_authorization_code(self, mock_access_token):
        # authlib raises an error if the authorization code is invalid
        mock_access_token.side_effect = OAuthError('invalid_grant')
        
        response = self.client.get(reverse('google_callback') + '?state=valid&code=invalid_code')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to authenticate with Google")

    def test_user_cancelled_login(self):
        # When user cancels, Google redirects back with error=access_denied
        # But our view currently just calls authorize_access_token without checking error first.
        # authlib will see error parameter and raise an exception.
        with patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token', side_effect=OAuthError('access_denied')):
            response = self.client.get(reverse('google_callback') + '?error=access_denied')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Failed to authenticate with Google")

    @patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token')
    def test_session_rotation_after_google_login(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'oauthuser@acme.test',
                'email_verified': True
            }
        }
        
        # Create a session
        self.client.session['pre_auth_data'] = 'secret'
        self.client.session.save()
        old_session_key = self.client.session.session_key
        
        response = self.client.get(reverse('google_callback'))
        
        # Session ID must change
        new_session_key = self.client.session.session_key
        self.assertNotEqual(old_session_key, new_session_key)
        self.assertEqual(response.status_code, 302)

    def test_logout_after_google_login(self):
        self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')
        self.assertIn('_auth_user_id', self.client.session)
        
        response = self.client.get(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(response.status_code, 302)

    @patch('authlib.integrations.django_client.apps.DjangoOAuth2App.authorize_access_token')
    def test_no_token_leakage_in_logs(self, mock_access_token):
        mock_access_token.return_value = {
            'access_token': 'SUPER_SECRET_TOKEN',
            'userinfo': {
                'email': 'oauthuser@acme.test',
                'email_verified': True
            }
        }
        
        with self.assertLogs(level='DEBUG') as log_capture:
            import logging
            logger = logging.getLogger('accounts.views')
            logger.debug('Callback received')
            response = self.client.get(reverse('google_callback'))
            
        self.assertEqual(response.status_code, 302)
        log_output = " ".join(log_capture.output)
        self.assertNotIn('SUPER_SECRET_TOKEN', log_output)
