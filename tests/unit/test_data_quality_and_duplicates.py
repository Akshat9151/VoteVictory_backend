import pytest
from app.models.data_collection import DataSubmission, SubmissionStatus
from app.services.data_collection_service import DataCollectionService


def test_quality_scoring_valid_record():
    service = DataCollectionService(None)
    sub = DataSubmission(
        citizen_name="John Doe",
        mobile="+12025550143",
        email="john.doe@example.com",
        voter_card_number="VOTER-123456",
        booth_no="12",
    )
    check = service._evaluate_quality(sub)
    assert check.is_valid_mobile is True
    assert check.is_valid_email is True
    assert check.is_valid_voter_card is True
    assert check.has_required_fields is True
    assert check.quality_percentage == 100.0


def test_quality_scoring_invalid_record():
    service = DataCollectionService(None)
    sub = DataSubmission(
        citizen_name="Jane Doe",
        mobile="123", # Invalid mobile
        email="not-an-email", # Invalid email
        voter_card_number="X", # Too short
        booth_no="12",
    )
    check = service._evaluate_quality(sub)
    assert check.is_valid_mobile is False
    assert check.is_valid_email is False
    assert check.is_valid_voter_card is False
    assert check.quality_percentage < 60.0
