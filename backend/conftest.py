import os

# Set before pytest-django triggers Django settings loading.
os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production')
