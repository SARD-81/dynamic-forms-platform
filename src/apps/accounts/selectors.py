from .models import User


def get_user_by_email(email):
    return User.objects.filter(email__iexact=email.strip()).first()


def get_user_by_username(username):
    return User.objects.filter(username=username.strip()).first()


def get_user_by_id(user_id):
    return User.objects.filter(pk=user_id).first()
