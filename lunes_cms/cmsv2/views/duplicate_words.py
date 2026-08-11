from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from ..models import AcceptedWordDuplicate, Word
from ..services import duplicate_words

#: Duplicate-vocabulary analysis and cleanup is restricted to superusers,
#: same as the rest of the admin's data-management actions (see e.g.
#: ``UserAdmin``/``UnitAdmin``) - not just any staff user.
superuser_required = user_passes_test(
    lambda user: user.is_active and user.is_superuser, login_url="admin:login"
)


@superuser_required
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


@superuser_required
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


@superuser_required
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
