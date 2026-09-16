from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from accounts.services import SystemIdentityService
from django.contrib.auth import get_user_model

class GuestAccessMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.employee_user = User.objects.create_user(
            email="employee@test.local",
            username="employee",
            password="password123",
            user_type="EMPLOYEE"
        )
        self.system_user = User.objects.create_user(
            email="system@test.local",
            username="system",
            password="password123",
            user_type="SYSTEM"
        )

    def test_anonymous_user_redirected_from_protected_view(self):
        # Dashboard should be protected
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_anonymous_user_can_access_public_view(self):
        # Landing page should be explicitly public
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        
        # Login page should be public
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_employee_can_access_protected_view(self):
        self.client.force_login(self.employee_user, backend='django.contrib.auth.backends.ModelBackend')
        # Dashboard is protected, so this would succeed (or redirect if missing Employee profile, but won't be 302 to login)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_system_user_cannot_access_interactively(self):
        self.client.force_login(self.system_user, backend='django.contrib.auth.backends.ModelBackend')
        # System users should be blocked by middleware with 403
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "System identities cannot be used for interactive access.", status_code=403)


class SystemIdentityServiceTests(TestCase):
    def test_get_inbound_email_processor_succeeds_when_present(self):
        # The user is provisioned automatically via data migration
        fetched_user = SystemIdentityService.get_inbound_email_processor()
        self.assertIsNotNone(fetched_user)
        self.assertEqual(fetched_user.user_type, "SYSTEM")
        self.assertEqual(fetched_user.username, "inbound_email_processor")

    def test_get_inbound_email_processor_raises_if_missing(self):
        # Delete the user to simulate missing migration or accidental deletion
        User.objects.filter(email=SystemIdentityService.INBOUND_EMAIL_PROCESSOR_EMAIL).delete()
        
        with self.assertRaises(RuntimeError):
            SystemIdentityService.get_inbound_email_processor()



