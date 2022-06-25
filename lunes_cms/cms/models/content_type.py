from django.contrib.contenttypes.models import ContentType

# Better representation of content type
ContentType.add_to_class("__str__", lambda c: c.name)
