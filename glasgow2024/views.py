from django.contrib.auth.views import (
    LoginView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)

from glasgow2024.forms import (
    Glasgow2024AuthenticationForm,
    Glasgow2024PasswordResetForm,
)


class GlasgowLoginView(LoginView):
    next_page = "/convention/login/"
    form_class = Glasgow2024AuthenticationForm


class GlasgowPasswordChangeView(PasswordChangeView):
    template_name = "glasgow2024/password_change_form.html"


class GlasgowPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "glasgow2024/password_change_done.html"


class GlasgowPasswordResetView(PasswordResetView):
    template_name = "glasgow2024/password_reset_form.html"
    form_class = Glasgow2024PasswordResetForm
    subject_template_name = "glasgow2024/password_reset_subject.txt"
    email_template_name = "glasgow2024/password_reset_email.html"


class GlasgowPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "glasgow2024/password_reset_confirm.html"


class GlasgowPasswordResetDoneView(PasswordResetDoneView):
    template_name = "glasgow2024/password_reset_done.html"


class GlasgowPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "glasgow2024/password_reset_complete.html"
