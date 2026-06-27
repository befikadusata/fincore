import re
from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    """Requires at least one uppercase letter and one digit."""

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one digit.')
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return 'Password must contain at least one uppercase letter and one digit.'
