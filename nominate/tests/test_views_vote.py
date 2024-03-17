from typing import Protocol, cast

import pytest
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.test import RequestFactory
from nominate import factories, models
from nominate.views.vote import VoteView
from pytest_lazy_fixtures import lf

# mark all tests in the module with @pytest.mark.django_db
pytestmark = pytest.mark.django_db

with_db = pytest.mark.django_db


class Submit(Protocol):
    def __call__(self, data: dict, extra: dict | None = None) -> HttpResponse:
        ...

    @property
    def success_status_code(self) -> int:
        ...


with_submitters = pytest.mark.parametrize(
    "submit_votes",
    [
        lf("submit_votes_http"),
    ],
)

full_page_only = pytest.mark.parametrize("view_class", [lf("full_page_view")])


@pytest.fixture(name="full_page_view")
def full_page_view_class():
    return VoteView


def basic_ranks(c: models.Category) -> dict[str, list[int]]:
    finalist_ids = c.finalist_set.values_list("id", flat=True)
    return make_ranks(
        c, [(finalist_id, rank + 1) for rank, finalist_id in enumerate(finalist_ids)]
    )


@pytest.fixture(name="submit_votes_http")
def make_submit_votes(member, tp, view_url) -> Submit:
    def do_submit(data: dict, extra: dict | None = None) -> HttpResponse:
        extra = {} if extra is None else extra
        tp.client.force_login(member.user)
        return tp.client.post(view_url, data, **extra)

    do_submit.success_status_code = 302
    return cast(Submit, do_submit)


def test_get_anonymous(tp, view_url):
    response = tp.client.get(view_url)
    assert response.status_code == 302
    assert response.url == f"{tp.reverse('login')}?next={view_url}"


def test_get_form(tp, member, view_url):
    tp.client.force_login(member.user)
    response = tp.get(view_url)
    assert response.status_code == 200


@with_submitters
def test_submittting_votes_response(c1, submit_votes: Submit):
    ranks = basic_ranks(c1)
    response = submit_votes(ranks)
    assert response.status_code == submit_votes.success_status_code


@with_submitters
def test_submittting_votes(c1, submit_votes: Submit, member):
    ranks = basic_ranks(c1)
    submit_votes(ranks)
    assert models.Rank.objects.count() == 5
    assert member.rank_set.count() == 5


@with_submitters
def test_submitting_valid_data_does_not_remove_other_members_votes(
    c1, submit_votes: Submit, member
):
    finalists = c1.finalist_set.all()
    other_member = factories.NominatingMemberProfileFactory.create()
    for i, finalist in enumerate(finalists):
        factories.RankFactory.create(
            finalist=finalist, membership=other_member, position=i
        )
    assert models.Rank.objects.count() == 5
    ranks = basic_ranks(c1)

    submit_votes(ranks)
    response = submit_votes(ranks)
    assert models.Rank.objects.count() == 10
    assert member.rank_set.count() == 5
    assert response.status_code == submit_votes.success_status_code


@with_submitters
def test_submitting_data_with_ip_headers_from_proxy_persists_ip(
    c1, submit_votes: Submit, member
):
    ranks = basic_ranks(c1)

    submit_votes(ranks, extra={"HTTP_X_FORWARDED_FOR": "111.111.111.111"})
    assert all(
        ip == "111.111.111.111"
        for ip in member.rank_set.values_list("voter_ip_address", flat=True)
    )


@with_submitters
def test_submitting_valid_data_clears_previous_votes_for_member(
    c1, member, submit_votes: Submit
):
    for i, finalist in enumerate(c1.finalist_set.all()):
        factories.RankFactory.create(finalist=finalist, membership=member, position=i)
    assert models.Rank.objects.count() == 5

    ranks = basic_ranks(c1)

    response = submit_votes(ranks)
    assert response.status_code == submit_votes.success_status_code
    assert models.Rank.objects.count() == 5


@pytest.fixture
def duplicate_ranks(c1):
    ranks = basic_ranks(c1)

    # make the first finalist rank the same as the last one; this is a duplicate ranking and must be
    # rejected.
    ranks[f"{c1.id}_{c1.finalist_set.first().id}"] = ranks[
        f"{c1.id}_{c1.finalist_set.last().id}"
    ]
    return ranks


@pytest.fixture
def rank_out_of_bounds(c1):
    ranks = basic_ranks(c1)

    # set the first rank to 0; 0 isn't an allowed rank.
    ranks[f"{c1.id}_{c1.finalist_set.first().id}"] = [0]
    return ranks


@pytest.fixture
def invalid_rank_data(c1):
    ranks = cast(dict, basic_ranks(c1))

    # set the first rank to a non-number
    ranks[f"{c1.id}_{c1.finalist_set.first().id}"] = "a"
    return ranks


@with_submitters
@pytest.mark.parametrize(
    "invalid_data",
    [lf("duplicate_ranks"), lf("rank_out_of_bounds"), lf("invalid_rank_data")],
)
def test_submitting_invalid_data_does_not_save(submit_votes: Submit, invalid_data):
    # Submit the form for the first time
    response = submit_votes(invalid_data)
    assert response.status_code == 200
    assert models.Rank.objects.count() == 0


@with_submitters
@pytest.mark.parametrize(
    "invalid_data",
    [lf("duplicate_ranks"), lf("rank_out_of_bounds"), lf("invalid_rank_data")],
)
def test_submitting_invalid_data_is_nondestructive(
    c1, c2, submit_votes: Submit, invalid_data
):
    factories.RankFactory.create(finalist=c1.finalist_set.first())
    factories.RankFactory.create(finalist=c2.finalist_set.first())

    # Submit the form for the first time
    response = submit_votes(invalid_data)
    assert models.Rank.objects.count() == 2
    assert response.status_code == 200


@with_submitters
@pytest.mark.parametrize(
    "invalid_data",
    [lf("duplicate_ranks"), lf("rank_out_of_bounds"), lf("invalid_rank_data")],
)
def test_series_of_submission_consistency(c1, submit_votes: Submit, invalid_data):
    # Submit the form for the first time
    response = submit_votes(invalid_data)
    assert response.status_code == 200
    assert models.Rank.objects.count() == 0

    # Modify invalid_data if necessary based on the response
    # all of our invalid data has a horked _first_ rank; that's easier here.
    invalid_data[f"{c1.id}_{c1.finalist_set.first().id}"] = 100

    # Submit the form for the second time
    response = submit_votes(invalid_data)
    assert response.status_code == 200
    assert models.Rank.objects.count() == 0

    # Now define valid data, could be the modifications needed after two invalid attempts
    valid_data = basic_ranks(c1)

    # Submit the form for the third time, now with valid data
    response = submit_votes(valid_data)
    assert response.status_code == submit_votes.success_status_code
    assert models.Rank.objects.count() == 5


def make_ranks(
    category: models.Category, data: list[tuple[int, int]]
) -> dict[str, list[int]]:
    ranks = {}
    for finalist_id, rank in data:
        ranks[f"{category.id}_{finalist_id}"] = [rank]
    return ranks


@pytest.fixture(name="election")
def make_election():
    return factories.ElectionFactory.create(state="voting")


@pytest.fixture(name="c1")
def make_category_1(election):
    category = factories.CategoryFactory.create(election=election)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    return category


@pytest.fixture(name="c2")
def make_category_2(election):
    category = factories.CategoryFactory.create(election=election)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    factories.FinalistFactory.create(category=category)
    return category


@pytest.fixture(name="member")
def make_member(voting_user):
    return factories.NominatingMemberProfileFactory.create(user=voting_user)


@pytest.fixture(name="voting_user")
def make_user():
    user = factories.UserFactory.create()
    user.user_permissions.add(
        Permission.objects.get(codename="vote", content_type__app_label="nominate")
    )
    return user


@pytest.fixture(name="staff_user")
def make_staff_user():
    return factories.UserFactory.create(is_staff=True)


@pytest.fixture(name="staff")
def make_staff(staff_user):
    return factories.NominatingMemberProfileFactory(user=staff_user)


@pytest.fixture(name="request_factory")
def make_request_factory():
    return RequestFactory()


@pytest.fixture
def view_url(tp, election):
    return tp.reverse("election:vote", election_id=election.slug)
