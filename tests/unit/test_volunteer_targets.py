from app.schemas.volunteer import VolunteerLeaderboardEntry, VolunteerPerformanceOut


def test_volunteer_performance_calculations():
    daily_target = 200
    monthly_target = 5000
    daily_collection = 150
    monthly_collection = 4000
    approved = 3800
    rejected = 150
    duplicate = 50
    total = 4000

    achieve_pct = round((monthly_collection / monthly_target) * 100, 2)
    approval_rate = round((approved / total) * 100, 2)
    rejection_rate = round((rejected / total) * 100, 2)
    duplicate_rate = round((duplicate / total) * 100, 2)
    remaining = max(0, monthly_target - monthly_collection)

    perf = VolunteerPerformanceOut(
        volunteer_id="vol-1",
        volunteer_name="John Doe",
        volunteer_code="VOL-101",
        daily_target=daily_target,
        weekly_target=1200,
        monthly_target=monthly_target,
        daily_collection=daily_collection,
        weekly_collection=1000,
        monthly_collection=monthly_collection,
        total_submissions=total,
        approved_count=approved,
        rejected_count=rejected,
        duplicate_count=duplicate,
        achievement_percentage=achieve_pct,
        remaining_target=remaining,
        approval_rate=approval_rate,
        rejection_rate=rejection_rate,
        duplicate_rate=duplicate_rate,
        performance_trend="IMPROVING" if achieve_pct >= 80.0 else "STEADY",
    )

    assert perf.achievement_percentage == 80.0
    assert perf.remaining_target == 1000
    assert perf.approval_rate == 95.0
    assert perf.rejection_rate == 3.75
    assert perf.duplicate_rate == 1.25
    assert perf.performance_trend == "IMPROVING"


def test_volunteer_leaderboard_entry():
    entry = VolunteerLeaderboardEntry(
        rank=1,
        volunteer_id="v1",
        volunteer_name="Alice Smith",
        volunteer_code="VOL-101",
        area_name="North District",
        booth_number="12A",
        collected_count=4500,
        approved_count=4400,
        achievement_percentage=90.0,
        badge="GOLD",
    )
    assert entry.rank == 1
    assert entry.badge == "GOLD"
    assert entry.collected_count == 4500
