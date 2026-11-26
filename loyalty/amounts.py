"""Integer accounting: 100 minor units = 1 JetPoint = 1 KZT. No float arithmetic."""
import re
from decimal import Decimal
from rest_framework.exceptions import ValidationError


def to_minor(value):
    if isinstance(value, (float, bool)):
        raise ValidationError('Use an exact decimal amount, not a floating point value.')
    text = format(value, 'f') if isinstance(value, Decimal) else str(value)
    match = re.fullmatch(r'(-?)(\d+)(?:\.(\d{1,2}))?', text)
    if not match:
        raise ValidationError('Amount must have at most two decimal places.')
    result = int(match[2]) * 100 + int((match[3] or '').ljust(2, '0'))
    return -result if match[1] else result


def display(minor):
    sign = '-' if minor < 0 else ''
    minor = abs(minor)
    return f'{sign}{minor // 100}.{minor % 100:02d}'


def decimal_amount(minor):
    """Compatibility boundary for the existing Django order/payment Decimal columns."""
    return Decimal(display(minor))


def basis_points(percent):
    return to_minor(percent)


def rounded_ratio(numerator, denominator):
    return (numerator * 2 + denominator) // (denominator * 2) if denominator else 0


def allocate(amount, weights):
    total = sum(weights)
    if not total:
        return [0] * len(weights)
    result = [amount * weight // total for weight in weights]
    left = amount - sum(result)
    for index in sorted(range(len(weights)), key=lambda i: (-(amount * weights[i] % total), i))[:left]:
        result[index] += 1
    return result
