from django.utils.translation import ugettext_lazy as _


def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.mp3', '.aac', '.wav', '.m4a', '.wma', '.ogg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('File type not supported! Use: .mp3 .aac .wav .m4a .wma .ogg'))


def validate_file_size(value):
    from django.core.exceptions import ValidationError
    if value.size > (5 * 1024 * 1024):
        raise ValidationError(_('File too large! Max. 5 MB'))
