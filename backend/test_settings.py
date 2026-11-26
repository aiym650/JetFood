"""Fast password hashing ONLY for automated tests; never use to run a server."""
from .settings import *  # noqa: F401,F403

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
# Fast isolated tests recycle primary keys within one minute. Keep the dedicated
# support throttle; avoid sharing the generic per-user quota between unrelated tests.
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_RATES': {**REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'], 'user': '100000/min', 'anon': '100000/min'}}
