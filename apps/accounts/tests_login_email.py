"""Members who signed up with only an email get a generated username they
never chose, so the login form must accept the email as well."""
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()
PASSWORD = 'x9!Probe-pass'


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LoginWithEmailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='Steady8702', email='member@example.com', password=PASSWORD
        )

    def test_email_signs_in(self):
        self.assertEqual(authenticate(username='member@example.com', password=PASSWORD), self.user)

    def test_email_is_case_insensitive(self):
        self.assertEqual(authenticate(username='Member@Example.com', password=PASSWORD), self.user)

    def test_username_still_signs_in(self):
        self.assertEqual(authenticate(username='Steady8702', password=PASSWORD), self.user)

    def test_wrong_password_is_refused(self):
        self.assertIsNone(authenticate(username='member@example.com', password='wrong'))

    def test_unknown_email_is_refused(self):
        self.assertIsNone(authenticate(username='nobody@example.com', password=PASSWORD))

    def test_inactive_member_is_refused(self):
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(username='member@example.com', password=PASSWORD))

    def test_login_page_posts_an_email(self):
        resp = self.client.post(reverse('accounts:login'),
                                {'username': 'member@example.com', 'password': PASSWORD})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_page_labels_the_field(self):
        resp = self.client.get(reverse('accounts:login'))
        self.assertContains(resp, 'Email or username')
        self.assertContains(resp, '<h1')
