from django.urls import path

from . import views

app_name = "glasgow2024"

# Glasgow has a basically complete login implementation.
urlpatterns = [
    path("login/", views.GlasgowLoginView.as_view(), name="login"),
    path(
        "password_change/",
        views.GlasgowPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password_change/done/",
        views.GlasgowPasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "password_reset/",
        views.GlasgowPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        views.GlasgowPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.GlasgowPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.GlasgowPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
