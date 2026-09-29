from django import forms

from apps.core.models import Category
from apps.core.selectors import get_category_choices_for_owner
from apps.forms.models import Form

from .models import Process
from .selectors import get_available_forms_for_owner, get_process_steps_for_owner


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class ProcessManagementForm(forms.Form):
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
    process_type = forms.ChoiceField(choices=Process.ProcessType.choices)
    visibility = forms.ChoiceField(choices=Process.Visibility.choices)
    access_password = forms.CharField(
        required=False,
        strip=False,
        label="Access password",
        help_text=(
            "Required for private processes. When editing a private draft, "
            "leave blank to keep the current password."
        ),
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = get_category_choices_for_owner(owner=owner)

    def clean_title(self):
        return self.cleaned_data["title"].strip()


class ProcessStepFormChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.title} ({obj.get_status_display()})"


class ProcessStepManagementForm(forms.Form):
    form = ProcessStepFormChoiceField(
        queryset=Form.objects.none(),
        label="Form",
        help_text=(
            "You can compose your own forms while the process is a draft. "
            "Every step form must be published before the process can be published."
        ),
    )

    def __init__(self, *args, owner, process, **kwargs):
        super().__init__(*args, **kwargs)
        used_form_ids = get_process_steps_for_owner(
            owner=owner,
            process_id=process.pk,
        ).values_list("form_id", flat=True)
        self.fields["form"].queryset = get_available_forms_for_owner(owner=owner).exclude(
            pk__in=used_form_ids
        )
