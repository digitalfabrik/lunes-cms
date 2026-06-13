from django.db import migrations

CODENAMES = [
    "can_view_analytics",
    "view_sessiondurationreport",
]


def assign_permissions(apps, _schema_editor):
    """Assign analytics permissions to the Partnermanagement group."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        group = Group.objects.get(name="Partnermanagement")
    except Group.DoesNotExist:
        return

    permissions = Permission.objects.filter(
        codename__in=CODENAMES,
        content_type__app_label="analytics",
    )
    group.permissions.add(*permissions)


def remove_permissions(apps, _schema_editor):
    """Remove analytics permissions from the Partnermanagement group (rollback)."""
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        group = Group.objects.get(name="Partnermanagement")
    except Group.DoesNotExist:
        return

    permissions = Permission.objects.filter(
        codename__in=CODENAMES,
        content_type__app_label="analytics",
    )
    group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    """Assign the ``can_view_analytics`` permission to the Partnermanagement group."""

    dependencies = [
        ("analytics", "0010_add_can_view_analytics_permission"),
    ]

    operations = [
        migrations.RunPython(assign_permissions, reverse_code=remove_permissions),
    ]
