from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext as _

from ..models import AcceptedWordDuplicate, Word
from ..services import duplicate_words, remove_duplicate_word


def _word_link(word: Word) -> SafeString:
    return format_html(
        '<a href="{}">{}</a>', reverse("admin:cmsv2_word_change", args=[word.pk]), word
    )


@staff_member_required
def word_check_duplicate(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint backing the create-time "a word like this already exists"
    warning on the Word add/change form (issue #531). Read-only, so it's a
    plain GET rather than something needing CSRF handling.
    """
    text = request.GET.get("word", "").strip()
    exclude_pk = request.GET.get("exclude_pk")
    if not text:
        return JsonResponse({"matches": []})

    queryset = Word.objects.filter(word=text)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)

    matches = [
        {
            "pk": word.pk,
            "display": str(word),
            "url": reverse("admin:cmsv2_word_change", args=[word.pk]),
        }
        for word in queryset.order_by("pk")
    ]
    return JsonResponse({"matches": matches})


@staff_member_required
def duplicated_vocabulary(request: HttpRequest) -> HttpResponse:
    """The "Analysis" page listing duplicate-vocabulary groups (issue #531)."""
    return render(
        request,
        "admin/cmsv2/duplicated_vocabulary.html",
        {
            **admin.site.each_context(request),
            "duplicate_groups": duplicate_words.find_duplicate_word_groups(),
        },
    )


@staff_member_required
def accept_word_duplicate(request: HttpRequest) -> HttpResponse:
    """
    Mark a duplicate-vocabulary group as an intentional duplicate - e.g. the
    same word taught with a different example sentence in a different unit -
    so it stops showing up in the analysis section (issue #531).
    """
    if request.method == "POST":
        words = Word.objects.filter(pk__in=request.POST.getlist("word"))
        accepted = AcceptedWordDuplicate.objects.create()
        accepted.words.set(words)
        messages.success(request, _("The duplicate has been accepted as intentional."))
    return redirect("cmsv2:duplicated_vocabulary")


@staff_member_required
def delete_duplicate_word(request: HttpRequest) -> HttpResponse:
    """
    Review and perform deletion of a duplicate ``Word`` row (issue #531).

    This is a straight deletion of ``loser``, not a content merge — the
    kept word's own fields are never touched. GET renders a review page
    asking, for each unit the loser belongs to that the keeper doesn't,
    whether the keeper should be added to it (so the word doesn't silently
    disappear from that unit). POST performs the deletion.
    """
    keeper_pk = request.GET.get("keeper") or request.POST.get("keeper")
    loser_pk = request.GET.get("loser") or request.POST.get("loser")
    keeper = get_object_or_404(Word, pk=keeper_pk)
    loser = get_object_or_404(Word, pk=loser_pk)

    if keeper.pk == loser.pk:
        messages.error(request, _("Cannot delete a word as a duplicate of itself."))
        return redirect("cmsv2:duplicated_vocabulary")

    if request.method == "POST":
        add_to_unit_ids = {
            int(key[len("add_to_unit_") :])
            for key, value in request.POST.items()
            if key.startswith("add_to_unit_") and value == "yes"
        }
        remove_duplicate_word.apply_removal(keeper, loser, add_to_unit_ids)
        messages.success(
            request,
            _('The duplicate "%(word)s" has been deleted.') % {"word": loser.word},
        )
        return redirect("cmsv2:duplicated_vocabulary")

    preview = remove_duplicate_word.prepare_removal(keeper, loser)
    return render(
        request,
        "admin/cmsv2/delete_duplicate_word.html",
        {
            **admin.site.each_context(request),
            "preview": preview,
            "keeper_link": _word_link(keeper),
            "loser_link": _word_link(loser),
        },
    )
