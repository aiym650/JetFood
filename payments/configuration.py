from django.conf import settings
from backend.environment import public_origin_host


def configuration_status(values=None):
    names = ('FREEDOMPAY_MERCHANT_ID', 'FREEDOMPAY_SECRET_KEY', 'PAYMENTS_PUBLIC_URL')
    config = {name: getattr(settings, name) for name in names} if values is None else values
    missing = [name for name in names if not str(config.get(name, '')).strip()]
    problems = []
    if config.get('PAYMENTS_PUBLIC_URL'):
        try:
            public_origin_host(config['PAYMENTS_PUBLIC_URL'])
        except ValueError as exc:
            problems.append(str(exc))
    return {
        'configured': not missing and not problems,
        'missing': missing,
        'problems': problems,
        'credentials_verified': False,
    }
