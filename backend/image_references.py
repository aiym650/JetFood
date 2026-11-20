from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def validate_image_reference(value):
    if value.startswith(('/media/', '/assets/')) and '..' not in value and '\\' not in value:
        return
    URLValidator(schemes=['https', 'http'])(value)
