# -*- coding: UTF-8 -*-
from django.contrib.auth import get_user_model
from social_core.exceptions import AuthException


def associate_by_username(backend, details, user=None, *args, **kwargs):
    """
    associate user by username

    required to assign a user with an already created repository owner
    """
    if user:
        return None

    username = details.get('username')
    if username:
        users = get_user_model().objects.filter(username=username)
        if len(users) == 0:
            return None
        elif len(users) > 1:
            raise AuthException(backend, 'The given username is associated with another account')
        else:
            return {'user': users.first(), 'is_new': False}
