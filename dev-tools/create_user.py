user="lunes"
email="admin@lunes.app"
password="lunes"

from django.contrib.auth.models import User
if user not in User.objects.values_list("username", flat=True):
    User.objects.create_superuser(user, email, password)