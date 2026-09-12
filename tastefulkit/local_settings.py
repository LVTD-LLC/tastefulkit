from tastefulkit.settings import *  # noqa: F403

Q_CLUSTER = {"name": "tastefulkit-local", "orm": "default", "timeout": 120, "retry": 180}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
