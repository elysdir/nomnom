from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from ipware import get_client_ip
from render_block import render_block_to_string

from nominate import models
from nominate.forms import NominationForm
from nominate.tasks import send_ballot

from .base import NominatorView


class NominationView(NominatorView):
    template_name = "nominate/nominate.html"

    def get_context_data(self, **kwargs):
        form = kwargs.pop("form", None)
        if form is None:
            form = NominationForm(
                categories=list(self.categories()),
                queryset=self.profile().nomination_set.filter(
                    category__election=self.election()
                ),
            )
        ctx = {
            "form": form,
        }
        ctx.update(super().get_context_data(**kwargs))
        return ctx

    def get(self, request: HttpRequest, *args, **kwargs):
        if not self.election().user_can_nominate(request.user):
            self.template_name = "nominate/election_closed.html"
            self.extra_context = {"object": self.election()}

        return super().get(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request: HttpRequest, *args, **kwargs):
        if not self.election().user_can_nominate(request.user):
            messages.error(
                request, f"You do not have nominating rights for {self.election()}"
            )
            return redirect("election:index")

        profile = self.profile()
        client_ip_address, _ = get_client_ip(request=request)

        # Kind of hacky but works - the place on the page is passwed in the submit
        category_saved = request.POST.get("save_all", None)

        form = NominationForm(categories=list(self.categories()), data=request.POST)

        if form.is_valid():
            # We would clear out the existing nominations for this user, but we want to retain
            # existing nominations that are included in the new ballot, so that we don't lose the
            # admin's work to canonicalize them, or the IP address and creation times.
            #
            # So, we find the existing ones, and the save logic gets a bit more complicated. We look
            # at the signatures of our new nominations, and only delete the nominations that are
            # missing now.
            existing_nominations = profile.nomination_set.filter(
                category__election=self.election()
            )

            signatures = {n.signature: n for n in existing_nominations}

            # now, we're going to iterate through the formsets and save the nominations
            to_create: list[models.Nomination] = []

            for nomination in form.cleaned_data["nominations"]:
                nomination.nominator = profile
                nomination.nomination_ip_address = client_ip_address
                if nomination.signature not in signatures:
                    # only create them if we don't have this one already
                    to_create.append(nomination)
                else:
                    del signatures[
                        nomination.signature
                    ]  # only allow one match to be retained

            models.Nomination.objects.bulk_create(to_create)
            for to_remove in signatures.values():
                to_remove.delete()

            messages.success(request, "Your set of nominations was saved")

            if request.htmx:
                return HttpResponse(
                    render_block_to_string(
                        "nominate/nominate.html",
                        "form",
                        context=self.get_context_data(form=form),
                        request=request,
                    )
                )
            else:
                url = reverse(
                    "election:nominate",
                    kwargs={"election_id": self.kwargs.get("election_id")},
                )
                anchor = f"#{category_saved}"
                return redirect(f"{url}{anchor}")

        else:
            messages.warning(request, "Something wasn't quite right with your ballot")
            if request.htmx:
                return HttpResponse(
                    render_block_to_string(
                        "nominate/nominate.html",
                        "form",
                        context=self.get_context_data(form=form),
                        request=request,
                    )
                )
            else:
                return self.render_to_response(self.get_context_data(form=form))


class EmailNominations(NominatorView):
    def post(self, request: HttpRequest, *args, **kwargs):
        send_ballot.delay(
            self.election().id,
            self.profile().id,
        )
        messages.success(request, _("An email will be sent to you with your ballot"))

        return redirect("election:nominate", election_id=self.kwargs.get("election_id"))
