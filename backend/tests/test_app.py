from datetime import datetime, timezone

from fastapi.testclient import TestClient

from threef.app import TEMPLATE_VERSION, create_app


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


def test_submissions_persist_versioned_template_snapshots() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    events = client.get("/api/events").json()
    plan_event = next(event for event in events if event["name"] == "SeasonPlanSubmitted")
    plan_template = plan_event["payload"]["template"]
    assert plan_template["template_id"] == "season_plan"
    assert plan_template["version"] == TEMPLATE_VERSION
    assert "season_name" in plan_template["prompts"]
    assert "outcome" in plan_template["prompts"]

    calibration_event = next(event for event in events if event["name"] == "WeeklyCalibrationSubmitted")
    calibration_template = calibration_event["payload"]["template"]
    assert calibration_template["template_id"] == "weekly_calibration"
    assert calibration_template["version"] == TEMPLATE_VERSION
    assert "momentum_evidence" in calibration_template["prompts"]
    assert [item["label"] for item in calibration_template["scales"]["momentum"]][:2] == ["Clogged", "Toxic"]
    assert [item["label"] for item in calibration_template["scales"]["responsibility"]][-1] == "Unbreakable"

    # The exact template used is retained on the projection for the submission.
    latest_calibration = client.get("/api/dashboard/demo-member").json()["latest_calibration"]
    assert latest_calibration["template"] == calibration_template


def test_reference_template_catalog() -> None:
    client = TestClient(create_app())
    catalog = client.get("/api/reference/templates").json()
    assert set(catalog) == {"season_plan", "weekly_calibration"}
    assert catalog["season_plan"]["version"] == TEMPLATE_VERSION
    assert catalog["weekly_calibration"]["version"] == TEMPLATE_VERSION
    assert catalog["weekly_calibration"]["scales"] == client.get("/api/reference/scales").json()


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


def test_rejected_queued_command_reports_conflict_detail() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    # A queued duplicate for an already-submitted week is rejected with the detail
    # the offline outbox surfaces as a needs-attention conflict state.
    conflict = client.post("/api/calibrations", json=calibration_payload() | {"command_id": "read-queued-retry"})
    assert conflict.status_code == 409
    assert "already submitted" in conflict.json()["detail"]

    # Replaying the original command ID remains idempotent and never duplicates state.
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201
    assert client.get("/api/dashboard/demo-member").json()["calibration_count"] == 1


def test_only_assigned_coach_can_review_calibration() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    assigned_record = client.get("/api/coaches/coach-elias/participants/demo-member")
    assert assigned_record.status_code == 200
    calibration = assigned_record.json()["participant"]["latest_calibration"]
    assert calibration["aim"] == "Build a life ordered around faithful stewardship."
    assert calibration["unreleased_weight"] == "I am carrying frustration from an unfinished conversation."
    assert calibration["strikes"] == [{"action": "Complete the budget review", "measure": "30 focused minutes on Saturday"}]

    unassigned = client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "captain-review", "coach_id": "captain-silas", "feedback": "This must not be accepted.",
    })
    assert unassigned.status_code == 403
    assert client.get("/api/dashboard/demo-member").json()["latest_review"] is None

    assigned = client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "assigned-review", "coach_id": "coach-elias", "feedback": "Clarify the first strike before next week.", "request_revision": True,
    })
    assert assigned.status_code == 201
    assert assigned.json()["status"] == "revision_requested"
    latest_review = client.get("/api/dashboard/demo-member").json()["latest_review"]
    assert latest_review["coach_id"] == "coach-elias"
    assert latest_review["feedback"] == "Clarify the first strike before next week."
    assert latest_review["request_revision"] is True


def test_assigned_coach_reopens_week_and_preserves_submission_history() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    # A submitted week is immutable until the assigned Coach reopens it. A new
    # command for the same week conflicts, while replaying the original command
    # is idempotent (see test_rejected_queued_command_reports_conflict_detail).
    assert client.post("/api/calibrations", json=calibration_payload() | {"command_id": "read-1-resubmit"}).status_code == 409

    # A Coach who is not assigned cannot reopen another Coach's participant week.
    forbidden = client.post("/api/calibrations/demo-member/1/reopen", json={
        "command_id": "captain-reopen", "coach_id": "captain-silas", "reason": "This must not be accepted.",
    })
    assert forbidden.status_code == 403
    assert client.get("/api/dashboard/demo-member").json()["reopened_weeks"] == []

    # Reopening a week with no submission is rejected.
    assert client.post("/api/calibrations/demo-member/2/reopen", json={
        "command_id": "reopen-missing", "coach_id": "coach-elias", "reason": "Nothing submitted for this week.",
    }).status_code == 404

    # The assigned Coach requests a revision and reopens the correct weekly record.
    assert client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "review-before-reopen", "coach_id": "coach-elias", "feedback": "Clarify the first strike.", "request_revision": True,
    }).status_code == 201
    reopened = client.post("/api/calibrations/demo-member/1/reopen", json={
        "command_id": "reopen-week-1", "coach_id": "coach-elias", "reason": "Revise the first strike before next week.",
    })
    assert reopened.status_code == 201
    assert reopened.json()["status"] == "reopened"

    dashboard = client.get("/api/dashboard/demo-member").json()
    assert dashboard["reopened_weeks"] == [1]
    assert dashboard["current_week"] == 1

    # The week cannot be reopened twice while it awaits resubmission.
    assert client.post("/api/calibrations/demo-member/1/reopen", json={
        "command_id": "reopen-twice", "coach_id": "coach-elias", "reason": "Reopen it again anyway.",
    }).status_code == 409

    # The participant resubmits the reopened week with revised content.
    revised = calibration_payload() | {
        "command_id": "read-2",
        "aim": "Rebuild the season around the first strike.",
        "strikes": [{"action": "Complete the budget review", "measure": "45 focused minutes on Saturday"}],
    }
    assert client.post("/api/calibrations", json=revised).status_code == 201

    after = client.get("/api/dashboard/demo-member").json()
    assert after["reopened_weeks"] == []
    assert after["calibration_count"] == 2
    assert after["latest_calibration"]["aim"] == "Rebuild the season around the first strike."

    # Both submissions remain in the append-only history with the original intact.
    submissions = [event for event in client.get("/api/events").json() if event["name"] == "WeeklyCalibrationSubmitted"]
    assert len(submissions) == 2
    assert submissions[0]["payload"]["aim"] == "Build a life ordered around faithful stewardship."
    assert submissions[1]["payload"]["aim"] == "Rebuild the season around the first strike."


def test_development_account_switcher_projection() -> None:
    client = TestClient(create_app(development_mode=True))
    accounts = client.get("/api/development/accounts").json()
    assert {(account["name"], account["role"]) for account in accounts} == {
        ("Administrator Amos", "administrator"), ("Marcus", "participant"), ("Coach Elias", "coach"), ("Captain Silas", "captain")
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


def test_captain_can_only_view_assigned_coach_status_without_calibration_content() -> None:
    client = TestClient(create_app())
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201

    status_record = client.get("/api/captains/captain-silas/coaches/coach-elias/status")
    assert status_record.status_code == 200
    record = status_record.json()
    assert record["coach"] == {"member_id": "coach-elias", "name": "Coach Elias"}
    assert record["summary"] == {
        "participant_count": 1,
        "plans_submitted": 1,
        "calibrations_submitted": 1,
        "calibrations_reviewed": 0,
    }
    assert record["participants"] == [{
        "member_id": "demo-member",
        "name": "Marcus",
        "season_plan_status": "submitted",
        "calibration": {"week": 1, "review_status": "awaiting_review"},
    }]
    serialized = str(record)
    assert "Build a life ordered" not in serialized
    assert "unreleased_weight" not in serialized
    assert "strikes" not in serialized

    assert client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "captain-status-review", "coach_id": "coach-elias", "feedback": "Keep protecting the conversation you cleared.",
    }).status_code == 201
    reviewed = client.get("/api/captains/captain-silas/coaches/coach-elias/status").json()
    assert reviewed["summary"]["calibrations_reviewed"] == 1
    assert reviewed["participants"][0]["calibration"]["review_status"] == "reviewed"

    assert client.post("/api/crucibles/demo-crucible/members", json={
        "command_id": "other-captain", "member_id": "captain-judah", "name": "Captain Judah", "role": "captain",
    }).status_code == 201
    assert client.get("/api/captains/captain-judah/coaches/coach-elias/status").status_code == 403
    assert client.get("/api/captains/captain-silas/coaches/demo-member/status").status_code == 403


def test_weekly_due_state_projection_lifecycle() -> None:
    def client_on(day: str) -> TestClient:
        return TestClient(create_app(clock=lambda: datetime.fromisoformat(day).replace(tzinfo=timezone.utc)))

    # The seeded Crucible launches on 2026-07-07, so Week 1 is open with a 2026-07-14 due date.
    opened = client_on("2026-07-08").get("/api/participants/demo-member/weekly-due-state").json()
    assert opened["member_id"] == "demo-member"
    assert opened["current_week"] == 1
    assert opened["weeks"] == [{
        "week": 1, "opens_on": "2026-07-07", "due_on": "2026-07-14",
        "state": "opened", "submitted": False, "reviewed": False, "reopened": False,
    }]
    assert opened["counts"] == {"opened": 1, "due_soon": 0, "overdue": 0, "submitted": 0, "reviewed": 0}

    due_soon = client_on("2026-07-12").get("/api/participants/demo-member/weekly-due-state").json()
    assert due_soon["weeks"][0]["state"] == "due_soon"

    overdue = client_on("2026-07-20").get("/api/participants/demo-member/weekly-due-state").json()
    assert overdue["current_week"] == 2
    assert [item["state"] for item in overdue["weeks"]] == ["overdue", "due_soon"]
    assert overdue["counts"]["overdue"] == 1

    client = client_on("2026-07-08")
    assert client.post("/api/season-plans", json=plan_payload()).status_code == 201
    assert client.post("/api/calibrations", json=calibration_payload()).status_code == 201
    submitted = client.get("/api/participants/demo-member/weekly-due-state").json()
    assert submitted["weeks"][0]["state"] == "submitted"
    assert submitted["weeks"][0]["submitted"] is True
    assert submitted["counts"]["submitted"] == 1

    assert client.post("/api/calibrations/demo-member/1/review", json={
        "command_id": "due-review", "coach_id": "coach-elias", "feedback": "Clear and honest.",
    }).status_code == 201
    reviewed = client.get("/api/participants/demo-member/weekly-due-state").json()
    assert reviewed["weeks"][0]["state"] == "reviewed"
    assert reviewed["weeks"][0]["reviewed"] is True
    assert reviewed["counts"]["reviewed"] == 1

    # Reopening returns the week to the participant's action queue while preserving history.
    assert client.post("/api/calibrations/demo-member/1/reopen", json={
        "command_id": "due-reopen", "coach_id": "coach-elias", "reason": "Clarify the first strike.",
    }).status_code == 201
    reopened = client.get("/api/participants/demo-member/weekly-due-state").json()
    assert reopened["weeks"][0] == {
        "week": 1, "opens_on": "2026-07-07", "due_on": "2026-07-14",
        "state": "opened", "submitted": False, "reviewed": False, "reopened": True,
    }


def test_weekly_due_state_is_participant_only() -> None:
    client = TestClient(create_app())
    assert client.get("/api/participants/coach-elias/weekly-due-state").status_code == 422
    dashboard = client.get("/api/dashboard/coach-elias").json()
    assert dashboard["weekly_due"] is None


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
