import pytest
from app.models.election import ElectionStatus
from app.services.election_service import ALLOWED_TRANSITIONS


def test_election_state_machine_transitions():
    draft_allowed = ALLOWED_TRANSITIONS[ElectionStatus.DRAFT]
    assert ElectionStatus.SCHEDULED in draft_allowed
    assert ElectionStatus.CANCELLED in draft_allowed
    assert ElectionStatus.LIVE not in draft_allowed

    live_allowed = ALLOWED_TRANSITIONS[ElectionStatus.LIVE]
    assert ElectionStatus.CLOSED in live_allowed
    assert ElectionStatus.PAUSED in live_allowed
    assert ElectionStatus.DRAFT not in live_allowed

    published_allowed = ALLOWED_TRANSITIONS[ElectionStatus.RESULT_PUBLISHED]
    assert ElectionStatus.ARCHIVED in published_allowed
    assert ElectionStatus.LIVE not in published_allowed
