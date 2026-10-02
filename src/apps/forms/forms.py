from django import forms

from apps.core.models import Category
from apps.core.selectors import get_category_choices_for_owner

from .models import POSITIVE_INTEGER_MAX, Form, Question


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class FormManagementForm(forms.Form):
    title = forms.CharField(max_length=200)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    category = CategoryChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="Uncategorized",
    )
    visibility = forms.ChoiceField(choices=Form.Visibility.choices)
    access_password = forms.CharField(
        required=False,
        strip=False,
        label="Access password",
        help_text=(
            "Required for private forms. When editing a private draft, "
            "leave blank to keep the current password."
        ),
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = get_category_choices_for_owner(owner=owner)

    def clean_title(self):
        return self.cleaned_data["title"].strip()


class QuestionManagementForm(forms.Form):
    text = forms.CharField(
        label="Question text",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    question_type = forms.ChoiceField(choices=Question.QuestionType.choices)
    is_required = forms.BooleanField(required=False, label="Required")
    max_length = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=POSITIVE_INTEGER_MAX,
        label="Text max length",
        help_text="Used only for TEXT questions.",
    )
    min_value = forms.DecimalField(
        required=False,
        max_digits=18,
        decimal_places=6,
        label="Minimum value",
        help_text="Used only for NUMBER questions.",
    )
    max_value = forms.DecimalField(
        required=False,
        max_digits=18,
        decimal_places=6,
        label="Maximum value",
        help_text="Used only for NUMBER questions.",
    )

    def clean_text(self):
        return self.cleaned_data["text"].strip()


class QuestionOptionForm(forms.Form):
    label = forms.CharField(max_length=255)

    def clean_label(self):
        return self.cleaned_data["label"].strip()
