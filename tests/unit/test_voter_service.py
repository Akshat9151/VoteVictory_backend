import pytest
from app.core.exceptions import ConflictException
from app.schemas.voter import VoterCreate
from app.services.voter_service import VoterService


@pytest.mark.asyncio
async def test_add_voter_success(db_session, test_org):
    service = VoterService(db_session)
    voter_data = VoterCreate(
        name="Sunil Sharma",
        age=32,
        gender="Male",
        ward="Ward 04",
        mobile="+91 98888 77777",
        channel="WhatsApp",
        consent="Verified",
        source="Field Survey",
        house="House 42"
    )
    res = await service.add_voter(voter_data, organization_id=test_org.id)
    assert res.id.startswith("V-")
    assert res.name == "Sunil Sharma"
    assert res.channel == "WhatsApp"


@pytest.mark.asyncio
async def test_batch_voter_import_success(db_session, test_org):
    service = VoterService(db_session)
    batch = [
        {"name": "Voter One", "age": 25, "gender": "Male", "ward": "Ward 01", "mobile": "+91 91111 22222"},
        {"name": "Voter Two", "age": 28, "gender": "Female", "ward": "Ward 02", "mobile": "+91 93333 44444"},
    ]
    res = await service.add_voters_batch(batch, organization_id=test_org.id)
    assert len(res) == 2
    assert res[0].name == "Voter One"
    assert res[1].name == "Voter Two"


@pytest.mark.asyncio
async def test_batch_voter_import_duplicate_id_rejected(db_session, test_org):
    service = VoterService(db_session)
    # V-04-101 is already seeded
    batch = [
        {"id": "V-04-101", "name": "Duplicate Voter", "age": 40, "gender": "Male", "ward": "Ward 04"}
    ]
    with pytest.raises(ConflictException):
        await service.add_voters_batch(batch, organization_id=test_org.id)


@pytest.mark.asyncio
async def test_audience_split_calculation(db_session, test_org):
    service = VoterService(db_session)
    split = await service.get_audience_split(test_org.id)
    assert split.total >= 10
    assert split.whatsapp + split.sms == split.total
    assert split.whatsappPercent + split.smsPercent >= 99  # Rounding tolerance
