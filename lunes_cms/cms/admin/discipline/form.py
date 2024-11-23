from django import forms


class DisciplineChoiceField(forms.ModelMultipleChoiceField):
    """
    Custom form field in order to include parent nodes in string representation.
    Inherits from `forms.ModelMultipleChocieField`.
    """

    def label_from_instance(self, obj):
        if obj.parent:
            ancestors = [
                node.title for node in obj.parent.get_ancestors(include_self=True)
            ]
            ancestors.append(obj.title)
            return " \u2794 ".join(ancestors)
        return obj.title
