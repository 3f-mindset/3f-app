from fastapi.testclient import TestClient

from threef.app import create_app


def plan_payload() -> dict:
    return {
        "command_id": "plan-1",
        "member_id": "demo-member",
        "season_name": "The Stewardship Season",
        "review_day": "Sunday",
        "review_time": "18:00",
        "timezone": "America/New_York",
        "roles": ["Man", "Builder"],
        "values": ["Presence", "Courage"],
        "domains": [{
            "name": "Health",
            "current_reality": "Right now, my health lacks a repeatable rhythm.",
            "outcome": "By the end of this season, I will train four times per week.",
            "protected_time": "Monday, Tuesday, Thursday, Friday at 6:30am",
            "action": "Strength training",
            "boundary": "No late scrolling before training days",
            "evidence": "Four completed training sessions",
            "weekly_actions": ["Train four times"],
            "scoreboard_measure": "4 workouts completed",
        }],
        "eliminations": [{"action": "reduce", "commitment": "Late-night scrolling"}],
    }


def calibration_payload() -> dict:
    return {
        "command_id": "read-1",
        "member_id": "demo-member",
        "week": 1,
        "aim": "Build a life ordered around faithful stewardship.",
        "momentum_level": "clearing",
        "momentum_evidence": "I addressed a conversation I had been avoiding.",
        "meaningful_moment": "Dinner with my family without my phone.",
        "why_it_mattered": "I was fully present instead of distracted.",
        "value_in_focus": "Presence",
        "value_most_neglected": "Courage",
        "role_reads": [{"role": "Man", "level": "grounded", "evidence": "I kept my morning and evening commitments."}],
        "avoided": "I avoided the difficult budget review.",
        "drain": "Late work messages drained more attention than they should have.",
        "unreleased_weight": "I am carrying frustration from an unfinished conversation.",
        "role_to_forge": "Man",
        "strikes": [{"action": "Complete the budget review", "measure": "30 focused minutes on Saturday"}],
        "scoreboard": {"Health": "green"},
    }


def test_pilot_flow_and_idempotency() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    # Replaying an offline command is safe and does not duplicate its event.
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201
    dashboard = client.get("/api/dashboard/demo-member").json()
    assert dashboard["calibration_count"] == 1
    assert dashboard["latest_calibration"]["momentum_level"] == "clearing"
    assert client.post("/api/calibrations/demo-member/1/review", json={"command_id": "review-1", "coach_id": "coach-elias", "feedback": "Keep protecting the conversation you cleared."}).status_code == 201
    events = client.get("/api/events").json()
    assert [event["name"] for event in events][-3:] == [
        "SeasonPlanSubmitted", "WeeklyCalibrationSubmitted", "WeeklyCalibrationReviewed"
    ]


def test_calibration_requires_plan() -> None:
    client = TestClient(create_app())
    response = client.post("/api/calibrations", json=calibration_payload())
    assert response.status_code == 409


def test_only_assigned_coach_can_review_calibration() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    unassigned = client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "captain-review", "coach_id": "captain-silas", "feedback": "This must not be accepted.",
    })
    assert unassigned.status_code == 403
    assert client.get("/api/dashboard/demo-member").json()["latest_review"] is None

    assigned = client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "assigned-review", "coach_id": "coach-elias", "feedback": "Keep protecting the conversation you cleared.",
    })
    assert assigned.status_code == 201
    assert client.get("/api/dashboard/demo-member").json()["latest_review"]["coach_id"] == "coach-elias"


def test_development_account_switcher_projection() -> None:
    client = TestClient(create_app(development_mode=True))
    accounts = client.get("/api/development/accounts").json()
    assert {(account["name"], account["role"]) for account in accounts} == {
        ("Marcus", "participant"), ("Coach Elias", "coach"), ("Captain Silas", "captain")
    }
    coach_dashboard = client.get("/api/dashboard/coach-elias").json()
    assert coach_dashboard["role"] == "coach"
    assert coach_dashboard["direct_reports"] == [{"member_id": "demo-member", "name": "Marcus", "role": "participant"}]
    participant_record = client.get("/api/coaches/coach-elias/participants/demo-member")
    assert participant_record.status_code == 200
    assert participant_record.json()["participant"]["name"] == "Marcus"
    assert client.get("/api/coaches/coach-elias/participants/captain-silas").status_code == 403
    production_client = TestClient(create_app(development_mode=False))
    assert production_client.get("/api/development/accounts").status_code == 404


def test_crucible_relationships_and_channel_boundaries() -> None:
    client = TestClient(create_app())
    assert client.post("/api/crucibles", json={
        "command_id": "alpha-crucible", "crucible_id": "alpha", "name": "The Ordered Life Season",
        "review_week_start": "2026-09-01", "refinement_week_start": "2026-09-08", "launch_date": "2026-09-15",
    }).status_code == 201
    for command_id, member_id, name, role in [
        ("alpha-captain", "captain-ada", "Captain Ada", "captain"),
        ("alpha-coach", "coach-ben", "Coach Ben", "coach"),
        ("alpha-student-one", "student-cai", "Cai", "participant"),
        ("alpha-student-two", "student-dee", "Dee", "participant"),
    ]:
        assert client.post("/api/crucibles/alpha/members", json={"command_id": command_id, "member_id": member_id, "name": name, "role": role}).status_code == 201
    assert client.post("/api/crucibles/alpha/coach-assignments", json={"command_id": "alpha-coach-link", "member_id": "student-cai", "mentor_id": "coach-ben"}).status_code == 201
    assert client.post("/api/crucibles/alpha/captain-assignments", json={"command_id": "alpha-captain-link", "member_id": "coach-ben", "mentor_id": "captain-ada"}).status_code == 201
    assert client.post("/api/crucibles/alpha/circles", json={
        "command_id": "alpha-buddy", "circle_id": "buddy-cai-dee", "name": "Cai and Dee", "kind": "buddy",
        "member_ids": ["student-cai", "student-dee"], "coach_sponsor_id": "coach-ben",
    }).status_code == 201
    assert client.post("/api/crucibles/alpha/channels", json={
        "command_id": "alpha-buddy-channel", "channel_id": "buddy-channel", "name": "Cai and Dee", "kind": "buddy",
        "member_ids": ["student-cai", "student-dee", "coach-ben"], "circle_id": "buddy-cai-dee",
    }).status_code == 201
    private_channel = client.post("/api/crucibles/alpha/channels", json={
        "command_id": "alpha-private", "channel_id": "private-channel", "name": "Private", "kind": "participant_private",
        "member_ids": ["student-cai", "coach-ben"],
    })
    assert private_channel.status_code == 422
    detail = client.get("/api/crucibles/alpha").json()
    assert {member["role"] for member in detail["members"]} == {"captain", "coach", "participant"}
    assert detail["circles"][0]["coach_sponsor_id"] == "coach-ben"
    assert detail["channels"][0]["member_ids"] == ["student-cai", "student-dee", "coach-ben"]
