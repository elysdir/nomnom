import unicodedata

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
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


def _unicode_ci_compare(s1, s2):
    """
    Perform case-insensitive comparison of two identifiers, using the
    recommended algorithm from Unicode Technical Report 36, section
    2.11.2(B)(2).
    """
    return (
        unicodedata.normalize("NFKC", s1).casefold()
        == unicodedata.normalize("NFKC", s2).casefold()
    )


class Glasgow2024PasswordResetForm(PasswordResetForm):
    field_order = ("email", "username", "password")
    email = forms.EmailField()
    username = forms.CharField(label="Ticket")

    def get_users(self, email: str):
        ticket = self.cleaned_data["username"]
        formatted_ticket = f"#{ticket}"
        email_field_name = UserModel.get_email_field_name()
        active_users = UserModel._default_manager.filter(
            **{
                "%s__iexact" % email_field_name: email,
                "convention_profile__member_number__in": (formatted_ticket, ticket),
                "is_active": True,
            }
        )
        return (
            u
            for u in active_users
            if _unicode_ci_compare(email, getattr(u, email_field_name))
        )

    @property
    def extra_email_context(self) -> dict[str, str]:
        return {"ticket": self.cleaned_data["username"]}
