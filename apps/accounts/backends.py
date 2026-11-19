"""Sign-in by email address.

Public signup asks only for an email and a password; the username is generated
(see username_generator.py). Django's ModelBackend only matches that generated
username, so this backend lets the same login form take the email instead.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None or '@' not in username:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Hash anyway, so a miss takes as long as a wrong password
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
