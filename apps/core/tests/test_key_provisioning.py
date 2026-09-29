from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from apps.api.auth import get_profile_for_api_key
from apps.core.models import Profile

pytestmark = pytest.mark.django_db


def test_new_account_has_recoverable_encrypted_key(user):
    profile = user.profile
    assert profile.has_api_key
    assert profile.api_key_encrypted
    key = profile.ensure_api_key()
    assert profile.has_api_key
    assert key not in profile.api_key_encrypted
    assert profile.ensure_api_key() == key
    assert get_profile_for_api_key(key).pk == profile.pk


def test_backfill_preserves_legacy_key_and_is_idempotent(user):
    profile = user.profile
    old_key = profile.rotate_api_key()
    Profile.objects.filter(pk=profile.pk).update(api_key_encrypted="")
    output = StringIO()
    call_command("provision_api_keys", stdout=output)
    profile.refresh_from_db()
    new_key = profile.ensure_api_key()
    assert new_key != old_key
    assert get_profile_for_api_key(old_key).pk == profile.pk
    assert get_profile_for_api_key(new_key).pk == profile.pk
    call_command("provision_api_keys", stdout=output)
    assert profile.ensure_api_key() == new_key
    assert old_key not in output.getvalue() and new_key not in output.getvalue()
    rotated = profile.rotate_api_key()
    assert get_profile_for_api_key(old_key) is None
    assert get_profile_for_api_key(new_key) is None
    assert get_profile_for_api_key(rotated).pk == profile.pk


def test_inactive_account_key_is_rejected(user):
    key = user.profile.ensure_api_key()
    User.objects.filter(pk=user.pk).update(is_active=False)
    assert get_profile_for_api_key(key) is None


def test_encryption_secret_rotation_supports_fallback(user, settings):
    key = user.profile.ensure_api_key()
    original_secret = settings.SECRET_KEY
    settings.SECRET_KEY = "replacement-secret"
    settings.SECRET_KEY_FALLBACKS = [original_secret]
    assert user.profile.ensure_api_key() == key


@pytest.mark.django_db(transaction=True)
def test_concurrent_provisioning_returns_one_key(user):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections

    Profile.objects.filter(user=user).update(api_key_encrypted="")

    def provision(_):
        close_old_connections()
        try:
            return Profile.objects.get(user_id=user.pk).ensure_api_key()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        keys = list(pool.map(provision, range(2)))
    assert keys[0] == keys[1]
    assert get_profile_for_api_key(keys[0]).user_id == user.pk
