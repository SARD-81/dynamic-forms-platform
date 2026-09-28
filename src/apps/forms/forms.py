from django import forms

from apps.core.models import Category
from apps.core.selectors import get_category_choices_for_owner

from .models import Form


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
