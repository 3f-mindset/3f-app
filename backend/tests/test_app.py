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


def build_alpha_channel_client() -> TestClient:
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
    assert client.post("/api/crucibles/alpha/circles", json={
        "command_id": "alpha-buddy", "circle_id": "buddy-cai-dee", "name": "Cai and Dee", "kind": "buddy",
        "member_ids": ["student-cai", "student-dee"], "coach_sponsor_id": "coach-ben",
    }).status_code == 201
    assert client.post("/api/crucibles/alpha/channels", json={
        "command_id": "alpha-buddy-channel", "channel_id": "buddy-channel", "name": "Cai and Dee", "kind": "buddy",
        "member_ids": ["student-cai", "student-dee", "coach-ben"], "circle_id": "buddy-cai-dee",
    }).status_code == 201
    return client


def test_authorized_channel_messaging_and_unread_state() -> None:
    client = build_alpha_channel_client()

    posted = client.post("/api/channels/buddy-channel/messages", json={
        "command_id": "message-1", "author_id": "student-cai", "body": "Morning, ready for the week?",
    })
    assert posted.status_code == 201
    assert posted.json()["status"] == "posted"

    # The author's own message never counts against their unread state.
    author_inbox = client.get("/api/members/student-cai/channels").json()
    buddy = next(channel for channel in author_inbox["channels"] if channel["channel_id"] == "buddy-channel")
    assert buddy["unread_count"] == 0
    assert buddy["last_message"]["body"] == "Morning, ready for the week?"

    # A fellow participant sees one unread message and its preview.
    reader_inbox = client.get("/api/members/student-dee/channels").json()
    reader_buddy = next(channel for channel in reader_inbox["channels"] if channel["channel_id"] == "buddy-channel")
    assert reader_buddy["unread_count"] == 1
    assert reader_inbox["unread_total"] == 1

    # Messages are returned in order with the body intact.
    messages = client.get("/api/members/student-dee/channels/buddy-channel/messages").json()
    assert messages["messages"][0]["body"] == "Morning, ready for the week?"
    assert messages["messages"][0]["author_id"] == "student-cai"
    assert messages["unread_count"] == 1

    # Marking read clears the unread count for that member only.
    assert client.post("/api/channels/buddy-channel/read", json={"command_id": "read-1", "member_id": "student-dee"}).status_code == 201
    after_read = client.get("/api/members/student-dee/channels").json()
    assert next(channel for channel in after_read["channels"] if channel["channel_id"] == "buddy-channel")["unread_count"] == 0

    # A Coach who is a channel member may post; an unassigned Captain may not.
    assert client.post("/api/channels/buddy-channel/messages", json={
        "command_id": "message-2", "author_id": "coach-ben", "body": "Hold the line together.",
    }).status_code == 201
    forbidden_post = client.post("/api/channels/buddy-channel/messages", json={
        "command_id": "message-outsider", "author_id": "captain-ada", "body": "This must not be accepted.",
    })
    assert forbidden_post.status_code == 403
    assert client.get("/api/members/captain-ada/channels").json()["channels"] == []
    assert client.get("/api/members/captain-ada/channels/buddy-channel/messages").status_code == 403

    # Persisted as durable domain events.
    events = client.get("/api/events").json()
    assert [event["name"] for event in events].count("ChannelMessagePosted") == 2
    assert [event["name"] for event in events].count("ChannelRead") == 1


def test_seeded_channels_are_relationship_scoped() -> None:
    client = TestClient(create_app())
    demo_inbox = client.get("/api/members/demo-member/channels").json()
    assert {channel["channel_id"] for channel in demo_inbox["channels"]} == {"whole-crucible", "coach-direct-demo"}

    # A member only sees channels they belong to; membership is explicit.
    captain_inbox = client.get("/api/members/captain-silas/channels").json()
    assert {channel["channel_id"] for channel in captain_inbox["channels"]} == {"whole-crucible"}
    assert client.get("/api/members/captain-silas/channels/coach-direct-demo/messages").status_code == 403


def test_notification_preferences_default_off_and_update() -> None:
    client = TestClient(create_app())
    prefs = client.get("/api/members/demo-member/notification-preferences").json()
    assert prefs["member_id"] == "demo-member"
    assert prefs["quiet_hours"] == {"enabled": False, "days": [], "start": "22:00", "end": "07:00", "behavior": "suppress"}
    assert prefs["devices"] == []
    assert prefs["push_enabled"] is False
    # Without an explicit preference, the timezone falls back to UTC.
    assert prefs["timezone"] == "UTC"

    updated = client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "prefs-1", "timezone": "America/New_York",
        "quiet_hours": {"enabled": True, "days": ["mon", "tue"], "start": "22:00", "end": "07:00", "behavior": "digest"},
    })
    assert updated.status_code == 200
    assert updated.json()["status"] == "updated"
    after = client.get("/api/members/demo-member/notification-preferences").json()
    assert after["timezone"] == "America/New_York"
    assert after["quiet_hours"] == {"enabled": True, "days": ["mon", "tue"], "start": "22:00", "end": "07:00", "behavior": "digest"}
    assert "NotificationPreferenceChanged" in [event["name"] for event in client.get("/api/events").json()]

    # Preference changes are validated rather than silently accepted.
    assert client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "prefs-bad-tz", "timezone": "Mars/Olympus", "quiet_hours": {"enabled": False},
    }).status_code == 422
    assert client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "prefs-bad-hour", "timezone": "UTC", "quiet_hours": {"enabled": True, "start": "25:00", "end": "07:00"},
    }).status_code == 422
    assert client.get("/api/members/unknown/notification-preferences").status_code == 404


def test_device_subscription_controls_push_versus_in_app_fallback() -> None:
    client = TestClient(create_app())
    body = {"notification_type": "calibration_reminder", "title": "Week 1 is open", "body": "Complete your read."}

    # With no subscribed device, the notification still records for in-app fallback.
    first = client.post("/api/members/demo-member/notifications", json=body | {"command_id": "n1"})
    assert first.status_code == 201
    assert first.json()["status"] == "in_app"
    assert first.json()["push"] is False

    assert client.post("/api/members/demo-member/notification-devices", json={
        "command_id": "d1", "device_id": "phone-1", "platform": "ios",
    }).status_code == 201
    assert client.get("/api/members/demo-member/notification-preferences").json()["push_enabled"] is True

    delivered = client.post("/api/members/demo-member/notifications", json=body | {"command_id": "n2"})
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["push"] is True

    # Unsubscribing a device returns the member to the in-app fallback.
    assert client.post("/api/members/demo-member/notification-devices/unsubscribe", json={
        "command_id": "d2", "device_id": "phone-1",
    }).status_code == 201
    assert client.post("/api/members/demo-member/notification-devices/unsubscribe", json={
        "command_id": "d3", "device_id": "phone-1",
    }).status_code == 404
    third = client.post("/api/members/demo-member/notifications", json=body | {"command_id": "n3"})
    assert third.json()["status"] == "in_app"

    center = client.get("/api/members/demo-member/notifications").json()
    assert center["total"] == 3
    assert [item["status"] for item in center["notifications"]] == ["in_app", "delivered", "in_app"]


def test_quiet_hours_are_evaluated_in_the_member_timezone() -> None:
    def client_at(iso: str) -> TestClient:
        return TestClient(create_app(clock=lambda: datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)))

    # 2026-07-08T02:00Z is 2026-07-07 22:00 in America/New_York (a Tuesday).
    client = client_at("2026-07-08T02:00:00")
    assert client.post("/api/members/demo-member/notification-devices", json={"command_id": "d1", "device_id": "phone-1"}).status_code == 201
    assert client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "p1", "timezone": "America/New_York",
        "quiet_hours": {"enabled": True, "days": ["tue"], "start": "21:00", "end": "07:00", "behavior": "suppress"},
    }).status_code == 200
    suppressed = client.post("/api/members/demo-member/notifications", json={
        "command_id": "n1", "notification_type": "calibration_reminder", "title": "Week open", "body": "Read.",
    })
    assert suppressed.json()["status"] == "suppressed"
    assert suppressed.json()["reason"] == "quiet_hours"

    # 2026-07-08T08:00Z is 04:00 in America/New_York, still inside the quiet
    # window, but it is 08:00 UTC, outside the same window for a UTC member.
    client = client_at("2026-07-08T08:00:00")
    assert client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "p1b", "timezone": "America/New_York",
        "quiet_hours": {"enabled": True, "days": ["tue"], "start": "21:00", "end": "07:00", "behavior": "suppress"},
    }).status_code == 200
    assert client.post("/api/members/demo-member/notifications", json={
        "command_id": "n1b", "notification_type": "calibration_reminder", "title": "Week open", "body": "Read.",
    }).json()["status"] == "suppressed"

    # The same instant is outside quiet hours when the member is on UTC, so the
    # policy is timezone-aware rather than server-local.
    utc_client = client_at("2026-07-08T08:00:00")
    assert utc_client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "p2", "timezone": "UTC",
        "quiet_hours": {"enabled": True, "days": ["tue"], "start": "21:00", "end": "07:00", "behavior": "suppress"},
    }).status_code == 200
    open_now = utc_client.post("/api/members/demo-member/notifications", json={
        "command_id": "n2", "notification_type": "calibration_reminder", "title": "Week open", "body": "Read.",
    })
    assert open_now.json()["status"] == "in_app"


def test_quiet_hours_digest_defers_to_the_window_end() -> None:
    client = TestClient(create_app(clock=lambda: datetime.fromisoformat("2026-07-08T02:00:00").replace(tzinfo=timezone.utc)))
    assert client.put("/api/members/demo-member/notification-preferences", json={
        "command_id": "p1", "timezone": "America/New_York",
        "quiet_hours": {"enabled": True, "days": [], "start": "21:00", "end": "07:00", "behavior": "digest"},
    }).status_code == 200
    digest = client.post("/api/members/demo-member/notifications", json={
        "command_id": "n1", "notification_type": "review_rhythm", "title": "Weekly review", "body": "Prepare your read.",
    })
    assert digest.json()["status"] == "digest"
    assert digest.json()["reason"] == "quiet_hours"
    # 07:00 America/New_York (EDT) on 2026-07-08 is 11:00 UTC.
    assert digest.json()["deliver_at"] == "2026-07-08T11:00:00+00:00"


def test_channel_mutes_suppress_social_alerts_without_silencing_workflow() -> None:
    client = build_alpha_channel_client()
    assert client.post("/api/members/student-dee/notification-devices", json={"command_id": "d1", "device_id": "phone-1"}).status_code == 201
    assert client.post("/api/members/student-dee/channel-mutes", json={"command_id": "m1", "channel_id": "buddy-channel"}).status_code == 201

    social = client.post("/api/members/student-dee/notifications", json={
        "command_id": "n1", "notification_type": "channel_message", "title": "New message", "body": "Open 3F.", "channel_id": "buddy-channel",
    })
    assert social.json()["status"] == "suppressed"
    assert social.json()["reason"] == "channel_muted"

    # Channel mutes apply only to social alerts, never required workflow notices.
    workflow = client.post("/api/members/student-dee/notifications", json={
        "command_id": "n2", "notification_type": "calibration_reminder", "title": "Week open", "body": "Read.",
    })
    assert workflow.json()["status"] == "delivered"

    # Suppressed alerts stay in the audit trail but are hidden from the center.
    assert client.get("/api/members/student-dee/notifications").json()["total"] == 1
    assert client.get("/api/members/student-dee/notifications?include_suppressed=true").json()["total"] == 2

    assert client.post("/api/members/student-dee/channel-mutes/unmute", json={"command_id": "m2", "channel_id": "buddy-channel"}).status_code == 201
    restored = client.post("/api/members/student-dee/notifications", json={
        "command_id": "n3", "notification_type": "channel_message", "title": "New message", "body": "Open 3F.", "channel_id": "buddy-channel",
    })
    assert restored.json()["status"] == "delivered"


def test_channel_mute_until_expires() -> None:
    client = TestClient(create_app(clock=lambda: datetime.fromisoformat("2026-07-08T12:00:00").replace(tzinfo=timezone.utc)))
    assert client.post("/api/members/demo-member/notification-devices", json={"command_id": "d1", "device_id": "phone-1"}).status_code == 201

    # A mute whose window already passed does not suppress new alerts.
    assert client.post("/api/members/demo-member/channel-mutes", json={
        "command_id": "m1", "channel_id": "whole-crucible", "muted_until": "2026-07-08T11:00:00Z",
    }).status_code == 201
    open_now = client.post("/api/members/demo-member/notifications", json={
        "command_id": "n1", "notification_type": "channel_message", "title": "t", "body": "b", "channel_id": "whole-crucible",
    })
    assert open_now.json()["status"] == "delivered"

    # A future mute suppresses until its expiry.
    assert client.post("/api/members/demo-member/channel-mutes", json={
        "command_id": "m2", "channel_id": "whole-crucible", "muted_until": "2026-07-08T13:00:00Z",
    }).status_code == 201
    muted = client.post("/api/members/demo-member/notifications", json={
        "command_id": "n2", "notification_type": "channel_message", "title": "t", "body": "b", "channel_id": "whole-crucible",
    })
    assert muted.json()["status"] == "suppressed"


def test_notification_authorization_boundaries() -> None:
    client = build_alpha_channel_client()

    # Only a channel member can mute it or receive its social alerts.
    assert client.post("/api/members/captain-ada/channel-mutes", json={"command_id": "m1", "channel_id": "buddy-channel"}).status_code == 403
    assert client.post("/api/members/captain-ada/notifications", json={
        "command_id": "n1", "notification_type": "channel_message", "title": "t", "body": "b", "channel_id": "buddy-channel",
    }).status_code == 403

    # A channel-message notification must name a channel; a workflow notice must not.
    assert client.post("/api/members/student-cai/notifications", json={
        "command_id": "n2", "notification_type": "channel_message", "title": "t", "body": "b",
    }).status_code == 422
    assert client.post("/api/members/student-cai/notifications", json={
        "command_id": "n3", "notification_type": "calibration_reminder", "title": "t", "body": "b", "channel_id": "buddy-channel",
    }).status_code == 422


def test_message_post_generates_generic_social_notifications_idempotently() -> None:
    client = build_alpha_channel_client()
    posted = client.post("/api/channels/buddy-channel/messages", json={
        "command_id": "msg-1", "author_id": "student-cai", "body": "Morning, ready for the week?",
    })
    assert posted.status_code == 201
    notified = {item["member_id"]: item["status"] for item in posted.json()["notified"]}
    assert notified == {"student-dee": "in_app", "coach-ben": "in_app"}

    # Replaying the command does not duplicate the message or its notifications.
    assert client.post("/api/channels/buddy-channel/messages", json={
        "command_id": "msg-1", "author_id": "student-cai", "body": "Morning, ready for the week?",
    }).status_code == 201
    event_names = [event["name"] for event in client.get("/api/events").json()]
    assert event_names.count("ChannelMessagePosted") == 1
    assert event_names.count("NotificationScheduled") == 2

    # The recipient's push payload stays generic and never leaks message content.
    notification = client.get("/api/members/student-dee/notifications").json()["notifications"][0]
    assert notification["notification_type"] == "channel_message"
    assert notification["category"] == "social"
    assert notification["body"] == "student-cai posted in Cai and Dee. Open 3F to read it."
    assert "Morning" not in notification["body"]

    # The author is never notified of his own message.
    assert client.get("/api/members/student-cai/notifications").json()["total"] == 0


def glossary_term_payload(**overrides: object) -> dict:
    payload = {
        "command_id": "glossary-1",
        "term_id": "refractory-lining",
        "author_id": "admin-amos",
        "title": "Refractory Lining",
        "definition": "The Values section of the 3F read. Values are demonstrated by what is protected under pressure.",
        "category": "practice",
        "tags": ["values", "3f"],
    }
    payload.update(overrides)
    return payload


def test_glossary_authoring_lifecycle_and_versions() -> None:
    client = TestClient(create_app())
    payload = glossary_term_payload()

    # Only an Administrator can author approved glossary knowledge.
    assert client.post("/api/glossary", json=payload | {"author_id": "coach-elias"}).status_code == 403
    assert client.post("/api/glossary", json=payload | {"author_id": "nobody"}).status_code == 404

    created = client.post("/api/glossary", json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert created.json()["version"] == 1

    # A draft is not approved knowledge: it is absent from published browse and
    # its detail is hidden from a regular member.
    assert "refractory-lining" not in {term["term_id"] for term in client.get("/api/glossary").json()["terms"]}
    assert client.get("/api/glossary/refractory-lining").status_code == 404
    assert client.get("/api/glossary/refractory-lining", params={"viewer_id": "demo-member"}).status_code == 404

    # An Administrator sees the draft; only the Administrator can publish it.
    draft_detail = client.get("/api/glossary/refractory-lining", params={"viewer_id": "admin-amos"}).json()
    assert draft_detail["term_status"] == "draft"
    assert [(version["version"], version["status"]) for version in draft_detail["versions"]] == [(1, "draft")]
    assert client.post("/api/glossary/refractory-lining/publish", json={"author_id": "demo-member"}).status_code == 403

    assert client.post("/api/glossary/refractory-lining/publish", json={"author_id": "admin-amos"}).status_code == 201

    live = client.get("/api/glossary/refractory-lining").json()
    assert live["status"] == "published"
    assert live["version"] == 1
    assert live["tags"] == ["values", "3f"]
    assert [version["status"] for version in live["versions"]] == ["published"]

    # Publishing twice without a new revision is rejected.
    assert client.post("/api/glossary/refractory-lining/publish", json={"author_id": "admin-amos"}).status_code == 409

    # A revision drafts a new version while the published version stays live.
    revision = client.post("/api/glossary/refractory-lining/revisions", json=payload | {
        "command_id": "glossary-2",
        "title": "Refractory Lining (Revised)",
        "definition": "The Values section of the 3F read, revised. Values are demonstrated by what is protected under pressure.",
    })
    assert revision.status_code == 201
    assert revision.json()["version"] == 2
    assert revision.json()["status"] == "draft"

    still_live = client.get("/api/glossary/refractory-lining").json()
    assert still_live["version"] == 1
    assert still_live["title"] == "Refractory Lining"
    assert still_live["has_draft"] is True

    assert client.post("/api/glossary/refractory-lining/publish", json={"author_id": "admin-amos"}).status_code == 201
    v2 = client.get("/api/glossary/refractory-lining").json()
    assert v2["version"] == 2
    assert v2["title"] == "Refractory Lining (Revised)"

    # Both versions remain in the append-only history, with the earlier one superseded.
    drafted = [event for event in client.get("/api/events").json() if event["name"] == "GlossaryTermDrafted" and event["payload"]["term_id"] == "refractory-lining"]
    assert [event["payload"]["version"] for event in drafted] == [1, 2]
    admin_detail = client.get("/api/glossary/refractory-lining", params={"viewer_id": "admin-amos"}).json()
    assert [(version["version"], version["status"]) for version in admin_detail["versions"]] == [(1, "superseded"), (2, "published")]

    # Archive removes the term from approved knowledge while retaining history.
    assert client.post("/api/glossary/refractory-lining/archive", json={"author_id": "demo-member"}).status_code == 403
    archived = client.post("/api/glossary/refractory-lining/archive", json={
        "author_id": "admin-amos", "reason": "Superseded by the new framework release.",
    })
    assert archived.status_code == 201
    assert archived.json()["status"] == "archived"
    assert client.get("/api/glossary/refractory-lining").status_code == 404
    assert "refractory-lining" not in {term["term_id"] for term in client.get("/api/glossary").json()["terms"]}
    archived_ids = [term["term_id"] for term in client.get("/api/glossary", params={"status_filter": "archived", "viewer_id": "admin-amos"}).json()["terms"]]
    assert archived_ids == ["refractory-lining"]

    # An archived term cannot be revised, published, or archived again.
    assert client.post("/api/glossary/refractory-lining/revisions", json=payload | {"command_id": "glossary-3"}).status_code == 409
    assert client.post("/api/glossary/refractory-lining/publish", json={"author_id": "admin-amos"}).status_code == 409
    assert client.post("/api/glossary/refractory-lining/archive", json={"author_id": "admin-amos"}).status_code == 409


def test_glossary_browse_search_and_authorization() -> None:
    client = TestClient(create_app())

    # Seeded, published framework terms are approved knowledge for every member.
    catalog = client.get("/api/glossary").json()
    assert catalog["status"] == "published"
    assert {term["term_id"] for term in catalog["terms"]} == {"clean-burn", "forge-read", "furnace-read", "slag-channel"}
    assert all(term["status"] == "published" for term in catalog["terms"])

    # Search is case-insensitive across title, definition, category, and tags.
    assert [term["term_id"] for term in client.get("/api/glossary", params={"q": "FURNACE"}).json()["terms"]] == ["furnace-read"]
    assert [term["term_id"] for term in client.get("/api/glossary", params={"q": "friction"}).json()["terms"]] == ["slag-channel"]
    assert [term["term_id"] for term in client.get("/api/glossary", params={"q": "Momentum Scale"}).json()["terms"]] == ["furnace-read"]
    assert client.get("/api/glossary", params={"q": "no-such-term"}).json()["terms"] == []

    # Category filters narrow the catalog.
    scales = client.get("/api/glossary", params={"category": "scale"}).json()
    assert {term["term_id"] for term in scales["terms"]} == {"furnace-read", "forge-read"}

    # Unpublished states require an Administrator viewer.
    assert client.get("/api/glossary", params={"status_filter": "draft"}).status_code == 403
    assert client.get("/api/glossary", params={"status_filter": "all", "viewer_id": "demo-member"}).status_code == 403
    assert client.get("/api/glossary", params={"status_filter": "draft", "viewer_id": "admin-amos"}).status_code == 200
    assert client.get("/api/glossary", params={"status_filter": "bogus", "viewer_id": "admin-amos"}).status_code == 422

    # A published term is readable by a regular member with its published history.
    detail = client.get("/api/glossary/clean-burn").json()
    assert detail["title"] == "Clean Burn"
    assert detail["version"] == 1
    assert detail["status"] == "published"
    assert [version["status"] for version in detail["versions"]] == ["published"]
    assert client.get("/api/glossary/unknown-term").status_code == 404
