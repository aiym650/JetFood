"""Local configuration without evaluating shell expressions or expanding secrets."""
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


def load_project_environment(path: Path):
    # Explicit process settings always win. Literal ${...} in keys stays literal.
    load_dotenv(path, override=False, interpolate=False, encoding='utf-8-sig')


def public_origin_host(value):
    """A callback origin must be HTTPS; local/private URLs cannot receive a provider callback."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError
        if parsed.port not in (None, 443) or host == 'localhost' or host.endswith(('.localhost', '.local')) or '*' in host:
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if '.' not in host or any(not label or not all(char.isascii() and (char.isalnum() or char == '-') for char in label) or label.startswith('-') or label.endswith('-') for label in host.split('.')):
                raise ValueError
        else:
            if not address.is_global:
                raise ValueError
        return host
    except (TypeError, ValueError):
        raise ValueError('PAYMENTS_PUBLIC_URL must be a public HTTPS origin, without a path, credentials or query.') from None
