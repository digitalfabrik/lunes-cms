from django.db import models
from django.utils.translation import ugettext_lazy as _

from PIL import Image, ImageFilter

from ..utils import get_image_tag
from ..validators import validate_multiple_extensions
from .static import Static, convert_umlaute_images
from .document import Document


class DocumentImage(models.Model):
    """
    Contains images and its titles that can be linked to a document object.
    """

    image = models.ImageField(
        upload_to=convert_umlaute_images, validators=[validate_multiple_extensions]
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="document_image"
    )
    confirmed = models.BooleanField(default=True, verbose_name="confirmed")

    def image_tag(self):
        """
        Image thumbnail to display a preview of a image in the editing section
        of the DocumentImage admin.

        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        return get_image_tag(self.image)

    image_tag.short_description = ""

    def save_original_img(self):
        """
        Function to save rough image with '_original' extension

        :param self: A handle to the :class:`model.DocumentImage`
        :type self: class: `model.DocumentImage`

        :return: None
        :rtype: None
        """
        name_elements = self.image.path.split(".")
        for elem in name_elements:
            if elem != name_elements[-1]:
                new_path = elem + "_"
        new_path = new_path + "original." + name_elements[-1]
        img = Image.open(self.image.path)
        img.save(new_path)

    def crop_img(self):
        """
        Function that crops the image and pastes it into a blurred background
        image

        :param self: A handle to the :class:`DocumentImage`
        :type self: class: `DocumentImage`

        :return: None
        :rtype: None
        """
        img_blurr = Image.open(self.image.path)
        img_cropped = Image.open(self.image.path)

        img_blurr = img_blurr.resize((Static.img_size[0], Static.img_size[1]))
        img_blurr = img_blurr.filter(ImageFilter.BoxBlur(Static.blurr_radius))

        if (
            img_cropped.width > Static.img_size[0]
            or img_cropped.height > Static.img_size[1]
        ):
            img_cropped.thumbnail(Static.img_size)
        elif (img_cropped.width / img_cropped.height) > (
            Static.img_size[0] / Static.img_size[1]
        ):
            img_cropped = img_cropped.resize(
                (
                    Static.img_size[0],
                    round(
                        (Static.img_size[0] / img_cropped.width) * img_cropped.height
                    ),
                )
            )
        else:
            img_cropped = img_cropped.resize(
                (
                    round(Static.img_size[1] / img_cropped.height) * img_cropped.width,
                    Static.img_size[1],
                )
            )

        offset = (
            ((img_blurr.width - img_cropped.width) // 2),
            ((img_blurr.height - img_cropped.height) // 2),
        )
        img_blurr.paste(img_cropped, offset)
        img_blurr.save(self.image.path)

    def __str__(self):
        """String representation of DocumentImage instance

        :return: title of document image instance
        :rtype: str
        """
        return self.document.word

    def save(self, *args, **kwargs):
        """Overwrite djangos save function to scale images into a
        uniform size that is defined in the Static module.
        """
        super(DocumentImage, self).save(*args, **kwargs)
        self.save_original_img()
        self.crop_img()

    class Meta:
        """
        Define user readable name of TrainingSet
        """

        verbose_name = _("image")
        verbose_name_plural = _("images")
