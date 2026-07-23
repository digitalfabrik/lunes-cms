from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Word


class DuplicatedVocabulary(Word):
    """
    Proxy of ``Word`` that exists only so its admin registration puts a link
    to the "Duplicated vocabulary" analysis page (issue #531) under its own
    "Analyse" sidebar section, rather than inside "Vocabulary Management v2".
    Carries no behaviour of its own — see ``analysis.admin.DuplicatedVocabularyAdmin``.
    """

    class Meta:
        """Meta class for the DuplicatedVocabulary proxy model."""

        proxy = True
        app_label = "analysis"
        verbose_name = _("Duplicated vocabulary")
        verbose_name_plural = _("Duplicated vocabulary")
