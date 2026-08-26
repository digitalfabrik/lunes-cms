import threading

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from tablib import Dataset
from tablib.exceptions import InvalidDimensions

from ..admins.word_import_resource import (
    import_words_from_csv,
    ImportSummary,
    validate_header_structure,
)
from ..models import Job
from ..services.audio_generation import drain_pending_audio
from ..services.image_generation import drain_pending_images
from ..services.sentence_generation import drain_pending_sentences


class ImportCSVForm(forms.Form):
    """
    Form for importing a CSV file.
    """

    job = forms.ModelChoiceField(
        queryset=Job.objects.all().order_by("name"),
        label=_("Job"),
        required=True,
    )
    csv_file = forms.FileField(
        label=_("Select CSV file"),
        help_text=_(
            "The file must be UTF-8 encoded and comma-separated. It should "
            'contain the columns "Einheit", "Artikel", "Vokabel" '
            'and "Beispielsatz", optionally also "Aussprache".'
        ),
    )


def _build_success_message(summary: ImportSummary) -> str:
    """
    Builds the pluralized success message shown after a completed CSV import.
    Each sentence is translated whole, so that leaving the reuse one out
    still reads correctly in every language.
    """
    words_phrase = ngettext(
        "%(count)s new word", "%(count)s new words", summary.words_created
    ) % {"count": summary.words_created}
    units_phrase = ngettext(
        "%(count)s new unit", "%(count)s new units", summary.units_created
    ) % {"count": summary.units_created}
    sentences = [
        _("Import successful! %(words)s, %(units)s created.")
        % {"words": words_phrase, "units": units_phrase}
    ]

    if summary.units_reused:
        sentences.append(
            ngettext(
                "%(count)s existing unit was extended.",
                "%(count)s existing units were extended.",
                summary.units_reused,
            )
            % {"count": summary.units_reused}
        )

    sentences.append(
        str(
            _(
                "Example sentences, audio and images are being generated in the "
                "background. This may take a few minutes..."
            )
        )
    )
    return " ".join(sentences)


def _generate_word_assets(word_ids: list[int], job_title: str) -> None:
    """
    Generates the missing assets for the imported words, in a thread.

    The order matters — audio can only be made once the sentence exists —
    and the drains must not run in parallel: each does a full ``Word.save()``,
    so concurrent ones would write back stale in-memory copies and clobber
    each other's file fields, re-triggering generation.
    """
    drain_pending_sentences(word_ids, job_title=job_title)
    drain_pending_audio(word_ids)
    drain_pending_images(word_ids, job_title=job_title)


def _report_dataset_issue(request: HttpRequest, data: Dataset) -> bool:
    """
    Checks whether the uploaded dataset can be imported at all, adding the
    appropriate user-facing message if not. Returns True if the caller
    should stop (nothing to import), False if the dataset is ready for
    ``import_words_from_csv``.
    """
    format_error = validate_header_structure(data.headers)
    if format_error:
        messages.error(request, format_error)
        return True
    if len(data) == 0:
        messages.warning(
            request, _("The file contains no entries. Nothing was imported.")
        )
        return True
    return False


def _build_context(
    request: HttpRequest, form: ImportCSVForm, job: Job | None, job_id: int | None
) -> dict:
    """
    Method to build the context for the admin view.
    """
    import_url = (
        reverse("cmsv2:import_csv_for_job", args=[job_id])
        if job_id
        else reverse("cmsv2:import_csv")
    )
    return {
        **admin.site.each_context(request),
        "form": form,
        "job": job,
        "title": _("CSV import for vocabulary"),
        "import_csv_url": import_url,
    }


@staff_member_required
def import_from_csv(request: HttpRequest, job_id: int | None = None) -> HttpResponse:
    """
    Method for importing vocabularies for a job from csv
    """
    job = get_object_or_404(Job, pk=job_id) if job_id else None

    if request.method != "POST":
        initial = {"job": job} if job else {}
        form = ImportCSVForm(initial=initial)
        if job:
            form.fields["job"].widget = forms.HiddenInput()
        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )

    form = ImportCSVForm(request.POST, request.FILES)
    if job:
        form.fields["job"].widget = forms.HiddenInput()

    if not form.is_valid():
        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )

    csv_file = form.cleaned_data["csv_file"]
    selected_job = form.cleaned_data["job"]
    try:
        data = Dataset()
        data.load(csv_file.read().decode("utf-8-sig"), format="csv")

        if _report_dataset_issue(request, data):
            return render(
                request,
                "admin/csv_form.html",
                _build_context(request, form, job, job_id),
            )

        # request.user is `User | AnonymousUser`, but this view is only
        # reachable by authenticated staff users.
        summary = import_words_from_csv(
            data, selected_job, request.user  # type: ignore[arg-type]
        )

        if summary.errors:
            error_summary = " | ".join(summary.errors[:5])
            messages.warning(
                request,
                _("Import completed with warnings: %(summary)s")
                % {"summary": error_summary},
            )
        else:
            messages.success(request, _build_success_message(summary))

        if summary.imported_word_ids:
            threading.Thread(
                target=_generate_word_assets,
                args=(summary.imported_word_ids, selected_job.name),
                daemon=True,
            ).start()
        return redirect(reverse("admin:cmsv2_job_change", args=[selected_job.pk]))

    except InvalidDimensions:
        messages.error(
            request,
            _(
                "Import failed. The size of the column or row doesn't fit the table dimensions. Please adjust your table and try again."
            ),
        )
        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )
    except UnicodeDecodeError:
        messages.error(
            request,
            _(
                "Import failed. The CSV file must be UTF-8 encoded. Please save it with UTF-8 encoding and try again."
            ),
        )
        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )
    except (AttributeError, IndexError, TypeError, ValueError) as e:
        messages.error(
            request,
            _("Import failed: %(e)s") % {"e": e},
        )

        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )
