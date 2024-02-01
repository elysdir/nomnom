from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

UserModel = get_user_model()


class Glasgow2024AuthenticationForm(AuthenticationForm):
    field_order = ("email", "username", "password")
    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "initial",
            {"username": "1000004", "email": "offline@offby1.net", "password": "fake"},
        )
        super().__init__(*args, **kwargs)

        # rewrite our label
        self.fields["username"].label = _("Ticket")

    def clean(self):
        username = self.cleaned_data.get("username")
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")

        if email and username and password:
            self.user_cache = authenticate(
                self.request, username=username, email=email, password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Please enter a correct email, ticket, and password."
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")

        return self.cleaned_data
