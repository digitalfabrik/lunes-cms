from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Word


class DuplicatedVocabulary(Word):
    """
    Proxy of ``Word`` that exists only so its admin registration puts a link
    to the "Open duplicates" analysis page (issue #531) under its own
    "Analyse" sidebar section, rather than inside "Vocabulary Management v2".
    Carries no behaviour of its own — see ``analysis.admin.DuplicatedVocabularyAdmin``.
    """

    class Meta:
        """Meta class for the DuplicatedVocabulary proxy model."""

        proxy = True
        app_label = "analysis"
        verbose_name = _("Open duplicates")
        verbose_name_plural = _("Open duplicates")
        permissions = [("can_view_duplicates", "Can view and manage duplicates")]


class AcceptedDuplicates(AcceptedWordDuplicate):
    """
    Proxy of ``AcceptedWordDuplicate`` that exists only so its admin
    registration puts a link to the accepted-duplicates list (issue #531)
    under the "Analyse" sidebar section, next to "Open duplicates". Carries
    no behaviour of its own — see ``analysis.admin.AcceptedDuplicatesAdmin``.
    """

    class Meta:
        """Meta class for the AcceptedDuplicates proxy model."""

        proxy = True
        app_label = "analysis"
        verbose_name = _("Accepted duplicates")
        verbose_name_plural = _("Accepted duplicates")
