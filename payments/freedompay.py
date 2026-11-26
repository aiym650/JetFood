"""Freedom Pay Kazakhstan Merchant API. No card data enters this adapter.

Protocol references: https://docs.freedompay.kz/overview-741636m0
https://docs.freedompay.kz/11620859e0 and /11620963e0
"""
import hashlib
import hmac
from secrets import token_hex
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from django.conf import settings
from rest_framework.exceptions import APIException


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = 'Payment provider unavailable. No payment has been confirmed. Retry status verification.'


def signature(script, values, secret=None):
    def flatten(value):
        if isinstance(value, dict):
            return [part for key in sorted(value) if key != 'pg_sig' for part in flatten(value[key])]
        if isinstance(value, list):
            return [part for item in value for part in flatten(item)]
        return [str(value) if value is not None else '']
    data = ';'.join([script, *flatten(values), secret if secret is not None else settings.FREEDOMPAY_SECRET_KEY])
    return hashlib.md5(data.encode('utf-8'), usedforsecurity=False).hexdigest()


def valid_signature(script, values):
    return bool(settings.FREEDOMPAY_SECRET_KEY and values.get('pg_sig') and
        hmac.compare_digest(signature(script, values), str(values['pg_sig'])))


def configured():
    from .configuration import configuration_status
    return configuration_status()['configured']


def _xml_value(element):
    if not len(element):
        return element.text or ''
    result = {}
    for child in element:
        value = _xml_value(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return result


def call(script, params):
    if not configured():
        raise ProviderUnavailable('Online payment is not configured. Contact support or choose cash for a new order.')
    values = {**params, 'pg_merchant_id': settings.FREEDOMPAY_MERCHANT_ID, 'pg_salt': token_hex(16)}
    values['pg_sig'] = signature(script, values)
    request = Request(f'https://api.freedompay.kz/{script}', data=urlencode(values).encode(), method='POST')
    try:
        with urlopen(request, timeout=settings.FREEDOMPAY_TIMEOUT) as response:
            raw = response.read(262145)
        if len(raw) > 262144 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('Invalid XML')
        root = ET.fromstring(raw)
        values = _xml_value(root)
        if root.tag != 'response' or not isinstance(values, dict) or not valid_signature(script, values):
            raise ValueError('Unverified provider response')
        return values
    except (OSError, TimeoutError, ET.ParseError, ValueError) as exc:
        # Unknown result: the caller persists the attempt and reconciles; never resubmit.
        raise ProviderUnavailable() from exc


def start(attempt):
    base = settings.PAYMENTS_PUBLIC_URL.rstrip('/')
    return_url = f'{settings.PAYMENTS_RETURN_URL}?order={attempt.payment.order_id}'
    result = call('init_payment.php', {
        'pg_order_id': attempt.reference, 'pg_amount': str(attempt.payment.amount), 'pg_currency': 'KZT',
        'pg_description': f'JetFood {attempt.payment.order.order_number}',
        'pg_result_url': f'{base}/api/payments/result.php',
        'pg_success_url': return_url, 'pg_failure_url': return_url,
        'pg_success_url_method': 'GET', 'pg_failure_url_method': 'GET',
        'pg_testing_mode': '1' if attempt.payment.is_test else '0',
        'pg_auto_clearing': '1', 'pg_lifetime': '3600',
    })
    redirect = urlparse(result.get('pg_redirect_url', ''))
    if result.get('pg_status') != 'ok' or not result.get('pg_payment_id') or redirect.scheme != 'https' or not (redirect.hostname or '').endswith('.freedompay.kz'):
        raise ProviderUnavailable('Payment page could not be verified. Check payment status before retrying.')
    return result


def fetch(attempt):
    return call('get_status3.php', {'pg_payment_id': attempt.provider_id} if attempt.provider_id else {'pg_order_id': attempt.reference})
