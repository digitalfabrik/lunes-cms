from __future__ import annotations

import threading
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import UploadedFile
from django.forms.boundfield import BoundField
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_POST
from tablib import Dataset
from tablib.exceptions import InvalidDimensions

from ..admins.image_prompt_info import render_image_prompt_info
from ..admins.word_import_resource import (
    import_words_from_csv,
    ImportSummary,
    validate_header_structure,
)
from ..areas import visible_jobs
from ..models import ImagePrompt, Job
from ..services.audio_generation import drain_pending_audio
from ..services.image_generation import (
    default_image_model,
    drain_pending_images,
    image_models,
    ImagePromptContext,
)
from ..services.sentence_generation import drain_pending_sentences
from .decorators import json_not_found, require_any_permission_json


def _image_prompt_label(image_prompt: ImagePrompt) -> str:
    """
    The name of a prompt in the dropdown, marking the default one like the
    dropdowns of the other image generation pages.
    """
    if image_prompt.is_default:
        default_label = _("default")
        return f"{image_prompt.name} ({default_label})"
    return str(image_prompt.name)


class ImportCSVForm(forms.Form):
    """
    Form for importing a CSV file.

    The job choices are restricted to the jobs the importing user may see, so
    nobody can import vocabulary into the job of another area.

    The images of all imported words are generated with the selected model
    and prompt (#1146), the default ones preselected.
    """

    #: Fields shown in the image generation card instead of with the file.
    IMAGE_FIELDS = ("image_model", "image_prompt")

    job = forms.ModelChoiceField(
        queryset=Job.objects.none(),
        label=_("Job"),
        required=True,
    )

    def __init__(
        self,
        *args: Any,
        user: AbstractBaseUser | AnonymousUser,
        fixed_job: Job | None,
        **kwargs: Any,
    ) -> None:
        if fixed_job:
            kwargs.setdefault("initial", {})["job"] = fixed_job
        super().__init__(*args, **kwargs)
        self.fields["job"].queryset = visible_jobs(  # type: ignore[attr-defined]
            user
        ).order_by("name")
        if fixed_job:
            self.fields["job"].widget = forms.HiddenInput()
        image_model = self.fields["image_model"]
        image_model.choices = [  # type: ignore[attr-defined]
            (model, model) for model in image_models()
        ]
        image_model.initial = default_image_model()
        image_prompt = self.fields["image_prompt"]
        image_prompt.queryset = ImagePrompt.selectable()  # type: ignore[attr-defined]
        image_prompt.initial = ImagePrompt.get_default()
        image_prompt.label_from_instance = _image_prompt_label  # type: ignore[attr-defined]

    @property
    def import_fields(self) -> list[BoundField]:
        """
        The fields that select what is imported.
        """
        return [field for field in self if field.name not in self.IMAGE_FIELDS]

    @property
    def image_fields(self) -> list[BoundField]:
        """
        The fields that select how the images of the imported words are
        generated.
        """
        return [self[name] for name in self.IMAGE_FIELDS]

    csv_file = forms.FileField(
        label=_("Select CSV file"),
        help_text=_(
            "The file must be UTF-8 encoded and comma-separated. It must "
            'contain the columns "Vokabel" and "Einheit", optionally also "Wortart", "Singularartikel", "Plural", "Pluralartikel", "Beispielsatz" and "Aussprache".'
        ),
    )
    image_model = forms.ChoiceField(
        label=_("Model"),
        widget=forms.Select(attrs={"class": "prompt-image-model"}),
    )
    image_prompt = forms.ModelChoiceField(
        queryset=ImagePrompt.objects.none(),
        label=_("Prompt"),
        empty_label=None,
        widget=forms.Select(attrs={"class": "prompt-image-prompt"}),
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


def _generate_word_assets(
    word_ids: list[int], job: Job, image_prompt: ImagePrompt, image_model: str
) -> None:
    """
    Generates the missing assets for the imported words, in a thread. The
    images are generated with the selected prompt and model.

    The order matters — audio can only be made once the sentence exists —
    and the drains must not run in parallel: each does a full ``Word.save()``,
    so concurrent ones would write back stale in-memory copies and clobber
    each other's file fields, re-triggering generation.
    """
    drain_pending_sentences(word_ids, job_title=job.name)
    drain_pending_audio(word_ids)
    drain_pending_images(
        word_ids, job=job, image_prompt=image_prompt, model=image_model
    )


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


def _image_prompt_context(job: Job | None) -> ImagePromptContext:
    """
    The image prompt context for the import, with placeholders for what only
    the CSV file tells.
    """
    return ImagePromptContext(
        word=str(_("[word]")),
        unit_title=str(_("[unit]")),
        job_title=job.name if job else str(_("[selected job]")),
    )


def _image_prompt_preview_url(job: Job | None) -> str:
    return (
        reverse("cmsv2:import_image_prompt_preview_for_job", args=[job.pk])
        if job
        else reverse("cmsv2:import_image_prompt_preview")
    )


def _image_prompt_info(job: Job | None) -> SafeString:
    """
    The image prompt explanation for the import. The model and prompt are
    selected in the form, and the preview follows the selected prompt.
    """
    return render_image_prompt_info(
        _image_prompt_context(job),
        preview_url=_image_prompt_preview_url(job),
        with_selection=False,
        with_additional_info=False,
        note=_(
            "For every imported word, the unit from its row and the selected job "
            "are used. A word listed in several units of the job gets no unit."
        ),
    )


def _build_context(request: HttpRequest, form: ImportCSVForm, job: Job | None) -> dict:
    """
    Builds the template context for the CSV import page.
    """
    import_url = (
        reverse("cmsv2:import_csv_for_job", args=[job.pk])
        if job
        else reverse("cmsv2:import_csv")
    )
    return {
        **admin.site.each_context(request),
        "form": form,
        "job": job,
        "title": _("CSV import for vocabulary"),
        "import_csv_url": import_url,
        "image_prompt_info": _image_prompt_info(job),
    }


def _try_run_import(request: HttpRequest, form: ImportCSVForm) -> bool:
    """
    Imports the file for the selected job, reports errors and warnings to the
    user, and returns whether the import was successful.
    """
    file: UploadedFile = form.cleaned_data["csv_file"]
    job: Job = form.cleaned_data["job"]
    try:
        data = Dataset()
        data.load(file.read().decode("utf-8-sig"), format="csv")

        if _report_dataset_issue(request, data):
            return False

        # request.user is `User | AnonymousUser`, but this view is only
        # reachable by authenticated users.
        summary = import_words_from_csv(
            data, job, request.user  # type: ignore[arg-type]
        )
    except InvalidDimensions:
        messages.error(
            request,
            _(
                "Import failed. The size of the column or row doesn't fit the table dimensions. Please adjust your table and try again."
            ),
        )
        return False
    except UnicodeDecodeError:
        messages.error(
            request,
            _(
                "Import failed. The CSV file must be UTF-8 encoded. Please save it with UTF-8 encoding and try again."
            ),
        )
        return False
    except (AttributeError, IndexError, TypeError, ValueError) as e:
        messages.error(request, _("Import failed: %(e)s") % {"e": e})
        return False

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
            args=(
                summary.imported_word_ids,
                job,
                form.cleaned_data["image_prompt"],
                form.cleaned_data["image_model"],
            ),
            daemon=True,
        ).start()
    return True


@login_required
@permission_required(("cmsv2.add_word", "cmsv2.add_unit"), raise_exception=True)
def import_from_csv(request: HttpRequest, job_id: int | None = None) -> HttpResponse:
    """
    Method for importing vocabularies for a job from csv
    """
    job = get_object_or_404(visible_jobs(request.user), pk=job_id) if job_id else None

    form = ImportCSVForm(
        request.POST or None, request.FILES or None, user=request.user, fixed_job=job
    )
    if form.is_valid() and _try_run_import(request, form):
        return redirect(
            reverse("admin:cmsv2_job_change", args=[form.cleaned_data["job"].pk])
        )

    return render(request, "admin/csv_form.html", _build_context(request, form, job))


@login_required
@require_any_permission_json("cmsv2.add_word")
@require_any_permission_json("cmsv2.add_unit")
@require_POST
def import_image_prompt_preview(
    request: HttpRequest, job_id: int | None = None
) -> JsonResponse:
    """
    AJAX endpoint returning the image prompt the import would send for the
    selected prompt (#1146), with placeholders for what only the CSV file
    tells. A word without a show-people decision gets the variant without
    people, so the preview never classifies.
    """
    job = visible_jobs(request.user).filter(pk=job_id).first() if job_id else None
    if job_id and job is None:
        return json_not_found(_("Job not found"))
    try:
        image_prompt = ImagePrompt.selected(request.POST.get("image_prompt"))
    except ValueError:
        return JsonResponse(
            {"error": str(_("The selected image prompt is not available."))},
            status=400,
        )
    return JsonResponse(
        {
            "prompt": _image_prompt_context(job).prompt(image_prompt=image_prompt),
            "show_people": None,
            "supports_show_people": image_prompt.supports_show_people,
        }
    )
