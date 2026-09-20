from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Project user model. Must exist before the first project migration."""

    email = models.EmailField(unique=True)
