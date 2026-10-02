from django import forms


class CategoryForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        strip=True,
        label="Category name",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
