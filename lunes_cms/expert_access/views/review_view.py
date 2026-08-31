from __future__ import annotations

from typing import cast

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Max, Min, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Review
from lunes_cms.cmsv2.models.static import (
    CannotBeAssessedReason,
    ChangeRequestReason,
    is_reviewer,
    RejectionReason,
    ReviewStatus,
)

#: The review states an expert can submit. :attr:`ReviewStatus.PENDING` is the
#: initial state of a review and can therefore not be chosen.
SUBMITTABLE_REVIEW_STATUSES = [
    ReviewStatus.APPROVED,
    ReviewStatus.CHANGE_REQUESTED,
    ReviewStatus.REJECTED,
    ReviewStatus.CANNOT_BE_ASSESSED,
]

REASONS_PER_STATUS = {
    ReviewStatus.CHANGE_REQUESTED: ChangeRequestReason,
    ReviewStatus.REJECTED: RejectionReason,
    ReviewStatus.CANNOT_BE_ASSESSED: CannotBeAssessedReason,
}


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
    #: :attr:`REASONS_PER_STATUS`, so it cannot be required on field
    #: level (see :meth:`ReviewForm.clean`). The reasons are grouped by the
    #: state they belong to, the decision dialog only shows the group of the
    #: chosen state. The choices are only enforced here, the model field
    #: accepts any string.
    reason = forms.ChoiceField(
        choices=[("", _("Please select a reason"))]
        + [
            (status.label, reasons.choices)
            for status, reasons in REASONS_PER_STATUS.items()
        ],
        label=_("reason"),
        required=False,
        # the groups are rendered in this order, which is how the dialog tells
        # which of them belongs to which state
        widget=forms.Select(
            attrs={"required": True, "data-statuses": " ".join(REASONS_PER_STATUS)}
        ),
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
        :attr:`REASONS_PER_STATUS` and discarded for all other states. The
        reason additionally has to be one of the reasons which are offered for
        the chosen state.

        :return: the cleaned data
        :rtype: dict
        """
        cleaned_data = super().clean() or {}
        review_status = cleaned_data.get("review_status")
        if review_status in list(REASONS_PER_STATUS):
            for field in ("reason", "comment"):
                if not cleaned_data.get(field) and field not in self.errors:
                    self.add_error(field, self.fields[field].error_messages["required"])
            reason = cleaned_data.get("reason")
            if reason and reason not in REASONS_PER_STATUS[review_status].values:
                self.add_error(
                    "reason", _("This reason cannot be given for this decision.")
                )
        else:
            cleaned_data["reason"] = ""
            cleaned_data["comment"] = ""
        return cleaned_data


def review_queue(user: User) -> QuerySet[Review]:
    """Returns the pending reviews of the given user, in the order they are presented in."""
    return Review.objects.filter(
        reviewer=user, review_status=ReviewStatus.PENDING
    ).order_by("review_priority", "assigned_at")


def move_to_end_of_queue(user: User, review_to_move: Review) -> None:
    """Moves the given review behind all other queued reviews of the user."""
    max_id = review_queue(user).aggregate(Max("review_priority", default=0))[
        "review_priority__max"
    ]
    Review.objects.filter(pk=review_to_move.pk).update(review_priority=max_id + 1)


def move_to_start_of_queue(user: User, review_to_move: Review) -> None:
    """Moves the given review in front of all other queued reviews of the user."""
    min_id = review_queue(user).aggregate(Min("review_priority", default=0))[
        "review_priority__min"
    ]
    Review.objects.filter(pk=review_to_move.pk).update(review_priority=min_id - 1)


@login_required
@user_passes_test(is_reviewer)
def review(request: HttpRequest) -> HttpResponse:
    """The expert review view

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    user = cast(User, request.user)
    form = None
    if request.method == "POST":
        instance = get_object_or_404(Review, id=request.POST.get("review_id"))
        if request.POST.get("skip"):
            move_to_end_of_queue(user, instance)
            messages.info(request, _("Review was skipped"))
            return redirect("expert_access:review")
        if request.POST.get("previous"):
            if previous_review := review_queue(user).last():
                move_to_start_of_queue(user, previous_review)
            messages.info(request, _("selected previous review"))
            return redirect("expert_access:review")

        form = ReviewForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Review was saved"))
            return redirect("expert_access:review")

    reviews = review_queue(user)
    current_review = reviews.first()
    num_reviews = reviews.count()

    return render(
        request,
        "review_view.html",
        {
            "user": user,
            "num_reviews": num_reviews,
            "current_review": current_review,
            "form": form or ReviewForm(instance=current_review),
        },
    )
