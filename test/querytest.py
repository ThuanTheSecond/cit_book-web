from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User

email = 'thaithuan@example.com'
username = 'kokie'

old = User.objects.filter(username = username)
print(old.count())