from django import forms

from .models import ReportSubscription


class ReportSubscriptionForm(forms.Form):
    frequency = forms.ChoiceField(choices=ReportSubscription.Frequency.choices)
    delivery_method = forms.ChoiceField(choices=ReportSubscription.DeliveryMethod.choices)
    email = forms.EmailField(required=False)
    endpoint_url = forms.URLField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("delivery_method")
        email = cleaned.get("email")
        endpoint_url = cleaned.get("endpoint_url")

        if method == ReportSubscription.DeliveryMethod.EMAIL:
            if not email:
                self.add_error("email", "An email target is required for EMAIL delivery.")
            if endpoint_url:
                self.add_error("endpoint_url", "API endpoint must be empty for EMAIL delivery.")
        elif method == ReportSubscription.DeliveryMethod.API:
            if not endpoint_url:
                self.add_error("endpoint_url", "An endpoint URL is required for API delivery.")
            if email:
                self.add_error("email", "Email target must be empty for API delivery.")
        return cleaned
