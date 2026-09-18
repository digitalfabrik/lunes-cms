"""
Helpers for building the content the area tests of the API work on.
"""

from lunes_cms.cmsv2.models import Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation

JOBS_ENDPOINT = "/api/v2/jobs/"
UNITS_ENDPOINT = "/api/v2/units/"
WORDS_ENDPOINT = "/api/v2/words/"
REGISTER_ENDPOINT = "/api/v2/areas/register/"
INFO_ENDPOINT = "/api/v2/areas/info/"


def released_unit_with_word(job, title, word_text):
    """
    Create a released unit of the job with one fully confirmed word.

    :param job: The job the unit belongs to
    :param title: The title of the unit
    :param word_text: The word itself
    :return: The created unit and word
    """
    unit = Unit.objects.create(title=title, released=True)
    unit.jobs.add(job)
    word = Word.objects.create(word=word_text, singular_article=1)
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    # ``save()`` resets the check status of an asset that is not there, so the
    # confirmations have to be written past it.
    Word.objects.filter(pk=word.pk).update(
        audio_check_status="CONFIRMED", image_check_status="CONFIRMED"
    )
    UnitWordRelation.objects.filter(pk=relation.pk).update(
        image_check_status="CONFIRMED"
    )
    word.refresh_from_db()
    return unit, word
