from django import forms
from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator


class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two password fields do not match.")
        return cleaned_data


class OTPVerificationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    code = forms.RegexField(
        regex=rf"^\d{{{settings.ACCOUNT_OTP_LENGTH}}}$",
        max_length=settings.ACCOUNT_OTP_LENGTH,
        min_length=settings.ACCOUNT_OTP_LENGTH,
        error_messages={
            "invalid": (
                f"Enter the {settings.ACCOUNT_OTP_LENGTH}-digit verification code."
            )
        },
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
            }
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class OTPResendForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_username(self):
        return self.cleaned_data["username"].strip()
