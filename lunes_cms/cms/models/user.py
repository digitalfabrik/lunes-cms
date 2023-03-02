from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser


class UserManager(BaseUserManager):
    def create_user(self, username, email, password):
        if not email:
            raise ValueError("_('Users must have an email address')")
        if not password:
            raise ValueError("_('Users must have a password')")
        user = self.model(email=self.normalize_email(email))
        user.set_username(username)
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser):
    """
    user model
    """

    username = models.CharField(default="", unique=True, max_length=30)
    email = models.EmailField(default="")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "password"]
    objects = UserManager()
