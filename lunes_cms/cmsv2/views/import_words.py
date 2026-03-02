from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..admins.word_import_resource import import_words_from_csv
from ..models import Job


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
            'The file should contain the columns "Einheit", "Artikel", "Vokabel" and "Beispielsatz".'
        ),
    )


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
        data.load(csv_file.read().decode("utf-8"), format="csv")
        created_count, updated_count, errors = import_words_from_csv(data, selected_job)

        if errors:
            error_summary = " | ".join(errors[:5])
            messages.warning(
                request,
                _("Import completed with warnings: %(summary)s")
                % {"summary": error_summary},
            )
        else:
            messages.success(
                request,
                _("Import successful! %(created)s new entries, %(updated)s updated.")
                % {"created": created_count, "updated": updated_count},
            )
        return redirect(reverse("admin:cmsv2_job_change", args=[selected_job.pk]))
    except ValueError as e:
        messages.error(
            request,
            _("Import failed: %(e)s") % {"e": e},
        )
        return render(
            request, "admin/csv_form.html", _build_context(request, form, job, job_id)
        )
