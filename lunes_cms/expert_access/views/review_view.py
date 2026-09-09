from __future__ import annotations

from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Review
from lunes_cms.cmsv2.models.static import ChangeRequestReason, ReviewStatus

#: The review states an expert can submit. :attr:`ReviewStatus.PENDING` is the
#: initial state of a review and can therefore not be chosen.
SUBMITTABLE_REVIEW_STATUSES = [
    ReviewStatus.APPROVED,
    ReviewStatus.CHANGE_REQUESTED,
    ReviewStatus.REJECTED,
    ReviewStatus.CANNOT_BE_ASSESSED,
]

#: The review states which an expert has to justify. They are submitted from
#: the decision dialog, which asks for a reason and a comment.
STATUSES_REQUIRING_A_REASON = [
    ReviewStatus.CHANGE_REQUESTED,
    ReviewStatus.REJECTED,
    ReviewStatus.CANNOT_BE_ASSESSED,
]


class ReviewForm(forms.ModelForm):
    """
    Form for the expert review view.
    """

    review_status = forms.ChoiceField(
        choices=[
            (status.value, status.label) for status in SUBMITTABLE_REVIEW_STATUSES
        ],
        label=_("review status"),
    )
    #: The reason is only mandatory for the states in
    #: :attr:`STATUSES_REQUIRING_A_REASON`, so it cannot be required on field
    #: level (see :meth:`ReviewForm.clean`). The choices are only enforced
    #: here, the model field accepts any string.
    reason = forms.ChoiceField(
        choices=[("", _("Please select a reason"))] + ChangeRequestReason.choices,
        label=_("reason"),
        required=False,
        widget=forms.Select(attrs={"required": True}),
    )

    class Meta:
        """
        Defining Meta description of `ReviewForm`.
        """

        model = Review
        fields = ["review_status", "reason", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "required": True}),
        }

    def clean(self) -> dict:
        """Validate the fields which are only used by the dialog states.

        Both the reason and the comment are mandatory for every state in
        :attr:`STATUSES_REQUIRING_A_REASON` and discarded for all other states.

        :return: the cleaned data
        :rtype: dict
        """
        cleaned_data = super().clean() or {}
        if cleaned_data.get("review_status") in STATUSES_REQUIRING_A_REASON:
            for field in ("reason", "comment"):
                if not cleaned_data.get(field) and field not in self.errors:
                    self.add_error(field, self.fields[field].error_messages["required"])
        else:
            cleaned_data["reason"] = ""
            cleaned_data["comment"] = ""
        return cleaned_data


def review(request: HttpRequest) -> HttpResponse:
    """The expert review view

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    form = None
    if request.method == "POST":
        instance = get_object_or_404(Review, id=request.POST.get("review_id"))
        form = ReviewForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            form = None

    reviews = Review.objects.filter(
        reviewer=request.user, review_status=ReviewStatus.PENDING
    ).order_by("assigned_at")
    current_review = reviews.first()
    num_reviews = reviews.count()

    return render(
        request,
        "review_view.html",
        {
            "user": request.user,
            "num_reviews": num_reviews,
            "current_review": current_review,
            "form": form or ReviewForm(instance=current_review),
        },
    )
