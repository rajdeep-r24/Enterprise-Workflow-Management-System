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
        self.client.login(username="employee@test.local", password="password123")
        # Dashboard is protected, so this would succeed (or redirect if missing Employee profile, but won't be 302 to login)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_system_user_cannot_access_interactively(self):
        self.client.login(username="system@test.local", password="password123")
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


from unittest.mock import patch

class GoogleOAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.valid_user = User.objects.create_user(
            email="valid@test.local",
            username="valid",
            password="password123",
            user_type="EMPLOYEE",
            is_active=True
        )
        # Mock employee profile dependency
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

        Employee.objects.create(
            user=self.valid_user,
            organization=org,
            department=dept,
            location=loc,
            designation=desig,
            role=role,
            employee_code="E001",
            joining_date="2020-01-01",
            is_active=True
        )

        self.inactive_user = User.objects.create_user(
            email="inactive@test.local",
            username="inactive",
            password="password123",
            user_type="EMPLOYEE",
            is_active=False
        )

        self.system_user = User.objects.create_user(
            email="sys@test.local",
            username="sys",
            password="password123",
            user_type="SYSTEM",
            is_active=True
        )

    def test_oauth_routes_reachable_anonymously(self):
        response = self.client.get(reverse('google_login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://accounts.google.com/'))

    def test_existing_email_password_login_works(self):
        response = self.client.post(reverse('login'), {
            'username': 'valid@test.local',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_google_login_success(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'valid@test.local',
                'email_verified': True
            }
        }
        session = self.client.session
        session['oauth_state'] = 'state123'
        session.save()
        response = self.client.get(reverse('google_callback') + "?state=state123&code=code123")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_unknown_google_email_denied(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'unknown@test.local',
                'email_verified': True
            }
        }
        response = self.client.get(reverse('google_callback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not associated with an active ForgeFlow account")

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_unverified_email_denied(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'valid@test.local',
                'email_verified': False
            }
        }
        response = self.client.get(reverse('google_callback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google email must be verified")

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_inactive_user_denied(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'inactive@test.local',
                'email_verified': True
            }
        }
        response = self.client.get(reverse('google_callback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ForgeFlow account is inactive")

    @patch('accounts.views.oauth.google.authorize_access_token')
    def test_system_user_denied(self, mock_access_token):
        mock_access_token.return_value = {
            'userinfo': {
                'email': 'sys@test.local',
                'email_verified': True
            }
        }
        response = self.client.get(reverse('google_callback'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System identities cannot use interactive authentication")
