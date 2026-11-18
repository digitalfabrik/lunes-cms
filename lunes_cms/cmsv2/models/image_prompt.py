"""
The prompts generated images are made from (#1143).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.template import Context, Engine, TemplateSyntaxError
from django.template.base import FilterExpression, Node, Variable
from django.template.smartif import TokenBase
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import BaseConstraint
    from django.template import Template

#: Engine the prompt templates are compiled with. It has no loaders, so a
#: prompt can't include or extend files, only use the built-in tags and
#: filters.
PROMPT_ENGINE = Engine()

#: Fields that hold the text of a prompt. They can't be changed any more once
#: the prompt has been used, see :attr:`ImagePrompt.used_at`.
LOCKED_FIELDS = (
    "supports_show_people",
    "prompt",
    "prompt_with_people",
    "prompt_without_people",
)

#: Name of the constraint that allows only one default prompt.
SINGLE_DEFAULT_CONSTRAINT = "single_default_image_prompt"

#: Variables a prompt is rendered with, see :meth:`ImagePrompt.render`.
PROMPT_VARIABLES = frozenset({"word", "job", "unit", "additional_info"})

#: Names every template context provides, plus the loop variable of ``for``.
BUILTIN_VARIABLES = frozenset({"True", "False", "None", "forloop"})

#: Attributes in which built-in tags keep the name of a variable they define,
#: e.g. ``{% cycle ... as name %}`` or ``{% url ... as name %}``.
BOUND_NAME_ATTRIBUTES = ("var_name", "variable_name", "asvar", "target")


def _referenced_variables(value: Any, names: set[str]) -> None:
    """
    Add the variables ``value`` reads to ``names``: a filter expression with
    its arguments, a variable, or the condition of an ``if`` tag. Nested
    lists, tuples and dicts are searched too; nodes are not, since
    :func:`template_variables` visits every node itself.
    """
    if isinstance(value, FilterExpression):
        _referenced_variables(value.var, names)
        for _func, args in value.filters:
            for is_lookup, arg in args:
                if is_lookup:
                    _referenced_variables(arg, names)
    elif isinstance(value, Variable):
        if value.lookups:
            names.add(value.lookups[0])
    elif isinstance(value, TokenBase):
        _referenced_variables(list(vars(value).values()), names)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _referenced_variables(item, names)
    elif isinstance(value, dict):
        _referenced_variables(list(value.values()), names)


def template_variables(template: Template) -> tuple[set[str], set[str]]:
    """
    The variables a compiled template reads, and the ones its tags define
    (loop variables, ``with`` and ``as`` names), whether or not a branch is
    ever rendered.
    """
    referenced: set[str] = set()
    bound: set[str] = set()
    for node in template.nodelist.get_nodes_by_type(Node):
        attributes = vars(node)
        bound.update(attributes.get("loopvars", ()))
        bound.update(attributes.get("extra_context", {}))
        bound.update(
            name
            for name in (attributes.get(attr) for attr in BOUND_NAME_ATTRIBUTES)
            if isinstance(name, str)
        )
        _referenced_variables(
            [
                value
                for key, value in attributes.items()
                if key not in ("token", "origin")
            ],
            referenced,
        )
    return referenced, bound


def _variable_errors(template: Template) -> list[ValidationError]:
    """
    Check that a prompt template uses ``word`` and no variable it isn't
    rendered with, since a misspelled one would silently render as nothing.
    """
    referenced, bound = template_variables(template)
    errors = []
    unknown = referenced - PROMPT_VARIABLES - BUILTIN_VARIABLES - bound
    if unknown:
        errors.append(
            ValidationError(
                _(
                    "Unknown variables: %(unknown)s. Available variables: word, "
                    "job, unit and additional_info."
                ),
                code="unknown_variable",
                params={"unknown": ", ".join(sorted(unknown))},
            )
        )
    if "word" not in referenced:
        errors.append(
            ValidationError(
                _("The prompt has to contain the word: %(variable)s"),
                code="word_missing",
                params={"variable": "{{ word }}"},
            )
        )
    return errors


class ImagePrompt(models.Model):
    """
    Model representing a prompt image generation can use.

    The text is a Django template rendered with ``word``, ``job``, ``unit``
    and ``additional_info``; all but ``word`` can be empty. The ban on text in
    the image and the instruction for the AI label are appended in code, so a
    prompt can't drop them by accident.

    A prompt that supports showing people has two complete variants instead
    of one, for words shown with and without people.
    """

    name = models.CharField(max_length=255, unique=True, verbose_name=_("name"))
    supports_show_people = models.BooleanField(
        default=False,
        verbose_name=_("supports show people"),
        help_text=_(
            "Whether the prompt has separate variants for images with and without "
            "people instead of a single prompt."
        ),
    )
    prompt = models.TextField(
        blank=True,
        verbose_name=_("prompt"),
        help_text=_("Used if the prompt doesn't support show people."),
    )
    prompt_with_people = models.TextField(
        blank=True,
        verbose_name=_("prompt with people"),
        help_text=_("Used for words that are shown with people."),
    )
    prompt_without_people = models.TextField(
        blank=True,
        verbose_name=_("prompt without people"),
        help_text=_("Used for words that are shown without people."),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("default"),
        help_text=_(
            "The prompt used unless another one is selected. Making a prompt the "
            "default removes the mark from the previous default."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
        help_text=_(
            "Inactive prompts are not offered for selection. The default prompt "
            "can't be deactivated."
        ),
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("first used at"),
        help_text=_(
            "When the prompt was first used to generate an image. From then on "
            "its text can't be changed any more, only copied."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        """
        Meta class for the ImagePrompt model.
        """

        verbose_name = _("image prompt")
        verbose_name_plural = _("image prompts")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=Q(is_default=True),
                name=SINGLE_DEFAULT_CONSTRAINT,
            ),
            models.CheckConstraint(
                condition=Q(is_default=False) | Q(is_active=True),
                name="default_image_prompt_is_active",
            ),
        ]

    def __str__(self) -> str:
        return str(self.name)

    @classmethod
    def get_default(cls) -> ImagePrompt:
        """
        The prompt used unless another one is selected.

        Migration 0051 creates it, and a default can only be replaced by
        another one, never unset, so there always is one.
        """
        return cls.objects.get(is_default=True)

    @classmethod
    def selectable(cls) -> models.QuerySet[ImagePrompt]:
        """
        The prompts editors can choose from when generating images: the active
        ones, the default first (#1146).
        """
        return cls.objects.filter(is_active=True).order_by("-is_default", "name")

    @classmethod
    def selected(cls, prompt_id: str | None) -> ImagePrompt:
        """
        The prompt an editor selected by its id, the default one if
        ``prompt_id`` is empty. Only :meth:`selectable` prompts can be
        selected.

        :raises ValueError: if there is no selectable prompt with that id
        """
        if not prompt_id:
            return cls.get_default()
        try:
            return cls.selectable().get(pk=int(prompt_id))
        except (ValueError, cls.DoesNotExist):
            raise ValueError(f"Unknown image prompt: {prompt_id!r}") from None

    @property
    def is_used(self) -> bool:
        """
        Whether an image has been generated with the prompt.
        """
        return self.used_at is not None

    def template_fields(self) -> tuple[str, ...]:
        """
        The fields holding the text this prompt is rendered from.
        """
        if self.supports_show_people:
            return ("prompt_with_people", "prompt_without_people")
        return ("prompt",)

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}
        for field in self.template_fields():
            text = getattr(self, field)
            if not text.strip():
                errors.setdefault(field, []).append(
                    ValidationError(_("This field is required."), code="required")
                )
                continue
            try:
                template = PROMPT_ENGINE.from_string(text)
            except TemplateSyntaxError as error:
                errors.setdefault(field, []).append(
                    ValidationError(
                        _("The prompt is not a valid template: %(error)s"),
                        code="invalid_template",
                        params={"error": error},
                    )
                )
                continue
            errors.setdefault(field, []).extend(_variable_errors(template))
        if self.is_default and not self.is_active:
            errors.setdefault("is_active", []).append(
                ValidationError(
                    _("The default prompt can't be deactivated."),
                    code="default_inactive",
                )
            )
        previous = ImagePrompt.objects.filter(pk=self.pk).first() if self.pk else None
        if previous is not None:
            if previous.is_default and not self.is_default:
                errors.setdefault("is_default", []).append(
                    ValidationError(
                        _(
                            "There always has to be a default prompt. Make another "
                            "prompt the default instead."
                        ),
                        code="default_unset",
                    )
                )
            if previous.is_used and any(
                getattr(previous, field) != getattr(self, field)
                for field in LOCKED_FIELDS
            ):
                errors.setdefault(NON_FIELD_ERRORS, []).append(
                    ValidationError(
                        _(
                            "The prompt has already been used to generate images, "
                            "so its text can't be changed any more. Copy it "
                            "instead."
                        ),
                        code="locked",
                    )
                )
        errors = {field: messages for field, messages in errors.items() if messages}
        if errors:
            raise ValidationError(errors)

    def get_constraints(
        self,
    ) -> list[tuple[type[models.Model], Sequence[BaseConstraint]]]:
        """
        The constraints form validation checks, without the single default:
        :meth:`save` removes the mark from the previous default, so making a
        prompt the default isn't a conflict.
        """
        return [
            (
                model,
                [
                    constraint
                    for constraint in constraints
                    if constraint.name != SINGLE_DEFAULT_CONSTRAINT
                ],
            )
            for model, constraints in super().get_constraints()
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the prompt. Making it the default removes the mark from the
        previous default in the same transaction.
        """
        with transaction.atomic():
            if self.is_default:
                ImagePrompt.objects.filter(is_default=True).exclude(pk=self.pk).update(
                    is_default=False
                )
            super().save(*args, **kwargs)

    def render(
        self,
        word: str,
        *,
        job: str | None = None,
        unit: str | None = None,
        additional_info: str | None = None,
        show_people: bool = False,
    ) -> str:
        """
        Render the prompt for a word.

        The prompt is plain text for the model, not HTML, so nothing is
        escaped. ``show_people`` picks the variant if the prompt supports
        showing people, and is ignored otherwise.
        """
        if not self.supports_show_people:
            text = self.prompt
        elif show_people:
            text = self.prompt_with_people
        else:
            text = self.prompt_without_people
        return PROMPT_ENGINE.from_string(text).render(
            Context(
                {
                    "word": word,
                    "job": job,
                    "unit": unit,
                    "additional_info": additional_info,
                },
                autoescape=False,
            )
        )

    def mark_used(self) -> None:
        """
        Record that an image has been generated with the prompt, which locks
        its text. Only the first use is recorded.
        """
        if self.used_at is None:
            now = timezone.now()
            ImagePrompt.objects.filter(pk=self.pk, used_at__isnull=True).update(
                used_at=now
            )
            self.used_at = now

    def copy(self) -> ImagePrompt:
        """
        Create an editable copy of the prompt, neither default nor used.
        """
        base_name = str(_("Copy of %(name)s") % {"name": self.name})[:240]
        name = base_name
        number = 2
        while ImagePrompt.objects.filter(name=name).exists():
            name = f"{base_name} ({number})"
            number += 1
        return ImagePrompt.objects.create(
            name=name,
            supports_show_people=self.supports_show_people,
            prompt=self.prompt,
            prompt_with_people=self.prompt_with_people,
            prompt_without_people=self.prompt_without_people,
        )
