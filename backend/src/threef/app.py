"""A local, event-sourced vertical slice of the 3F platform.

Infrastructure is deliberately in-memory here. The EventStore and projection
interfaces are the seam where DynamoDB, EventBridge, and Lambda adapters fit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import os
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator


class MomentumLevel(str, Enum):
    CLOGGED = "clogged"
    TOXIC = "toxic"
    PRESSURIZED = "pressurized"
    LEAKING = "leaking"
    VENTILATING = "ventilating"
    CLEARING = "clearing"
    FLOWING = "flowing"
    REFINED = "refined"
    CLEAN_BURNING = "clean_burning"


class ResponsibilityLevel(str, Enum):
    CRUSHED = "crushed"
    FRACTURED = "fractured"
    UNSTABLE = "unstable"
    HOLDING = "holding"
    SET = "set"
    GROUNDED = "grounded"
    STRUCTURED = "structured"
    FORGING = "forging"
    UNBREAKABLE = "unbreakable"


class ProgramRole(str, Enum):
    PARTICIPANT = "participant"
    COACH = "coach"
    CAPTAIN = "captain"
    ADMINISTRATOR = "administrator"


class CircleType(str, Enum):
    SMALL_GROUP = "small_group"
    BUDDY = "buddy"
    TRIAD = "triad"


class ChannelType(str, Enum):
    WHOLE_CRUCIBLE = "whole_crucible"
    SMALL_GROUP = "small_group"
    BUDDY = "buddy"
    TRIAD = "triad"
    COACH_DIRECT = "coach_direct"
    CAPTAIN_DIRECT = "captain_direct"
    LEADERSHIP = "leadership"
    PARTICIPANT_PRIVATE = "participant_private"


MOMENTUM_DEFINITIONS: dict[MomentumLevel, tuple[int, str, str]] = {
    MomentumLevel.CLOGGED: (1, "Clogged", "I feel backed up with thoughts and emotions I have not faced; everything in me feels heavy, slow, and resistant to movement."),
    MomentumLevel.TOXIC: (2, "Toxic", "I notice resentment, envy, or frustration leaking into everything; my fire burns dirty and distorts how I see things."),
    MomentumLevel.PRESSURIZED: (3, "Pressurized", "I am holding in too much; I have not released what is building, and it is starting to affect my focus and reactions."),
    MomentumLevel.LEAKING: (4, "Leaking", "I let some pressure out, but inconsistently; I vent in unproductive ways and still carry lingering weight."),
    MomentumLevel.VENTILATING: (5, "Ventilating", "I am starting to release what I carry in healthier ways; my mind clears in moments, but buildup still returns."),
    MomentumLevel.CLEARING: (6, "Clearing", "I actively face and process what has been sitting in me; my energy feels lighter and more usable."),
    MomentumLevel.FLOWING: (7, "Flowing", "I release tension as it arises; I do not let things sit long enough to distort my direction."),
    MomentumLevel.REFINED: (8, "Refined", "I convert pressure into clarity quickly; what once clogged me now fuels me with precision."),
    MomentumLevel.CLEAN_BURNING: (9, "Clean-Burning", "I operate with minimal internal waste; my energy moves freely, and my fire runs strong, steady, and true."),
}

RESPONSIBILITY_DEFINITIONS: dict[ResponsibilityLevel, tuple[int, str, str]] = {
    ResponsibilityLevel.CRUSHED: (1, "Crushed", "I have taken on more than I can hold; without structure, everything feels like it is collapsing on me."),
    ResponsibilityLevel.FRACTURED: (2, "Fractured", "I am trying to carry my responsibilities, but without consistency; things slip, and I feel scattered."),
    ResponsibilityLevel.UNSTABLE: (3, "Unstable", "I show up inconsistently; I handle some responsibilities well, but others fall through due to lack of structure."),
    ResponsibilityLevel.HOLDING: (4, "Holding", "I meet my core responsibilities; I am stable, but I have not built strength beyond maintaining."),
    ResponsibilityLevel.SET: (5, "Set", "I have created basic structure; I can rely on myself to handle what is in front of me without major failure."),
    ResponsibilityLevel.GROUNDED: (6, "Grounded", "I handle pressure with growing consistency; my routines support me, even when things get heavy."),
    ResponsibilityLevel.STRUCTURED: (7, "Structured", "I have built a reliable system; I do not just react, I operate with intention across my roles."),
    ResponsibilityLevel.FORGING: (8, "Forging", "I use responsibility to shape myself; pressure strengthens me instead of wearing me down."),
    ResponsibilityLevel.UNBREAKABLE: (9, "Unbreakable", "I carry weight with precision and control; no matter the load, I remain stable, effective, and sharp."),
}


TEMPLATE_VERSION = "1"

SEASON_WEEKS = 12
DUE_SOON_DAYS = 3
DUE_STATES = ("opened", "due_soon", "overdue", "submitted", "reviewed")

SEASON_PLAN_PROMPTS: dict[str, str] = {
    "season_name": "What will you call this 12-week season?",
    "current_reality": "Right now, this area is...",
    "outcome": "By the end of this 12-week season, I will have...",
    "protected_time": "What protected time will hold this work?",
    "action": "What action will happen inside that container?",
    "boundary": "What boundary protects the container?",
    "evidence": "What evidence shows the container is working?",
    "weekly_actions": "Each week, I will...",
    "scoreboard_measure": "How will this be scored green, yellow, or red?",
    "eliminations": "What commitment must be paused, delegated, finished, dropped, or reduced?",
    "review_rhythm": "When is the repeated weekly review day, time, and timezone?",
}

CALIBRATION_PROMPTS: dict[str, str] = {
    "aim": "What direction are you choosing to hold?",
    "momentum_evidence": "What specifically created that level this week?",
    "meaningful_moment": "What moment carried weight?",
    "why_it_mattered": "Why did it matter?",
    "value_in_focus": "Which value was most in focus this week?",
    "value_most_neglected": "Which value was most neglected this week?",
    "role_reads": "What actually happened that justifies this rating?",
    "avoided": "What did you avoid?",
    "drain": "What drained you more than it should have?",
    "unreleased_weight": "What are you still carrying that has not been released?",
    "role_to_forge": "Which role will you deliberately strengthen next?",
    "strikes": "What are your focused, measurable strikes for the next week?",
}


def scale_definitions() -> dict[str, list[dict[str, Any]]]:
    return {
        "momentum": [
            {"value": key.value, "level": value[0], "label": value[1], "definition": value[2]}
            for key, value in MOMENTUM_DEFINITIONS.items()
        ],
        "responsibility": [
            {"value": key.value, "level": value[0], "label": value[1], "definition": value[2]}
            for key, value in RESPONSIBILITY_DEFINITIONS.items()
        ],
    }


def season_plan_template() -> dict[str, Any]:
    return {"template_id": "season_plan", "version": TEMPLATE_VERSION, "prompts": dict(SEASON_PLAN_PROMPTS)}


def calibration_template() -> dict[str, Any]:
    return {
        "template_id": "weekly_calibration",
        "version": TEMPLATE_VERSION,
        "prompts": dict(CALIBRATION_PROMPTS),
        "scales": scale_definitions(),
    }


def template_catalog() -> dict[str, Any]:
    return {"season_plan": season_plan_template(), "weekly_calibration": calibration_template()}


@dataclass(frozen=True)
class DomainEvent:
    id: str
    stream_id: str
    stream_version: int
    name: str
    payload: dict[str, Any]
    occurred_at: str


class EventStore:
    """Append-only store with optimistic stream concurrency and idempotency."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._command_events: dict[str, list[DomainEvent]] = {}
        self._lock = Lock()

    def append(self, stream_id: str, expected_version: int, command_id: str, events: list[tuple[str, dict[str, Any]]]) -> list[DomainEvent]:
        with self._lock:
            if command_id in self._command_events:
                return self._command_events[command_id]
            current_version = sum(event.stream_id == stream_id for event in self._events)
            if current_version != expected_version:
                raise ValueError(f"Expected version {expected_version}; stream is at version {current_version}.")
            created = [
                DomainEvent(
                    id=str(uuid4()),
                    stream_id=stream_id,
                    stream_version=current_version + offset,
                    name=name,
                    payload=payload,
                    occurred_at=datetime.now(timezone.utc).isoformat(),
                )
                for offset, (name, payload) in enumerate(events, start=1)
            ]
            self._events.extend(created)
            self._command_events[command_id] = created
            return created

    def all(self) -> list[DomainEvent]:
        return list(self._events)

    def events_for_command(self, command_id: str) -> list[DomainEvent]:
        return list(self._command_events.get(command_id, []))


class SeasonDomain(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    current_reality: str = Field(min_length=10, max_length=1000)
    outcome: str = Field(min_length=10, max_length=1000)
    protected_time: str = Field(min_length=3, max_length=140)
    action: str = Field(min_length=3, max_length=300)
    boundary: str = Field(min_length=3, max_length=300)
    evidence: str = Field(min_length=3, max_length=300)
    weekly_actions: list[str] = Field(min_length=1, max_length=3)
    scoreboard_measure: str = Field(min_length=3, max_length=200)


class EliminationCommitment(BaseModel):
    action: str = Field(pattern="^(pause|delegate|finish|drop|reduce)$")
    commitment: str = Field(min_length=3, max_length=300)


class SeasonPlanCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    member_id: str = Field(min_length=1)
    season_name: str = Field(min_length=3, max_length=100)
    review_day: str = Field(min_length=3, max_length=40)
    review_time: str = Field(min_length=3, max_length=20)
    timezone: str = Field(min_length=3, max_length=80)
    roles: list[str] = Field(min_length=1, max_length=24)
    values: list[str] = Field(min_length=1, max_length=32)
    domains: list[SeasonDomain] = Field(min_length=1, max_length=8)
    eliminations: list[EliminationCommitment] = Field(min_length=1, max_length=5)

    @field_validator("roles", "values")
    @classmethod
    def unique_labels(cls, labels: list[str]) -> list[str]:
        cleaned = [label.strip() for label in labels if label.strip()]
        if len(cleaned) != len(set(label.lower() for label in cleaned)):
            raise ValueError("Entries must be unique.")
        return cleaned


class RoleRead(BaseModel):
    role: str = Field(min_length=2, max_length=80)
    level: ResponsibilityLevel
    evidence: str = Field(min_length=5, max_length=1000)


class Strike(BaseModel):
    action: str = Field(min_length=3, max_length=300)
    measure: str = Field(min_length=3, max_length=200)


class CalibrationCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    member_id: str = Field(min_length=1)
    week: int = Field(ge=1, le=12)
    aim: str = Field(min_length=10, max_length=1000)
    momentum_level: MomentumLevel
    momentum_evidence: str = Field(min_length=5, max_length=1000)
    meaningful_moment: str = Field(min_length=3, max_length=1000)
    why_it_mattered: str = Field(min_length=3, max_length=1000)
    value_in_focus: str = Field(min_length=2, max_length=80)
    value_most_neglected: str = Field(min_length=2, max_length=80)
    role_reads: list[RoleRead] = Field(min_length=1, max_length=12)
    avoided: str = Field(min_length=3, max_length=1000)
    drain: str = Field(min_length=3, max_length=1000)
    unreleased_weight: str = Field(min_length=3, max_length=1000)
    role_to_forge: str = Field(min_length=2, max_length=80)
    strikes: list[Strike] = Field(min_length=1, max_length=3)
    scoreboard: dict[str, str] = Field(default_factory=dict)


class CoachReviewCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    coach_id: str = Field(min_length=1)
    feedback: str = Field(min_length=5, max_length=2000)
    request_revision: bool = False


class ReopenCalibrationCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    coach_id: str = Field(min_length=1)
    reason: str = Field(min_length=5, max_length=2000)


class CreateCrucibleCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    crucible_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=120)
    review_week_start: str = Field(min_length=10, max_length=10)
    refinement_week_start: str = Field(min_length=10, max_length=10)
    launch_date: str = Field(min_length=10, max_length=10)


class EnrollMemberCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    member_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=100)
    role: ProgramRole


class AssignRelationshipCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    member_id: str = Field(min_length=3, max_length=80)
    mentor_id: str = Field(min_length=3, max_length=80)


class CreateCircleCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    circle_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=100)
    kind: CircleType
    member_ids: list[str] = Field(min_length=2, max_length=12)
    coach_sponsor_id: str | None = Field(default=None, min_length=3, max_length=80)

    @field_validator("member_ids")
    @classmethod
    def unique_members(cls, member_ids: list[str]) -> list[str]:
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("Circle members must be unique.")
        return member_ids


class CreateChannelCommand(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid4()))
    channel_id: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=100)
    kind: ChannelType
    member_ids: list[str] = Field(min_length=2, max_length=50)
    circle_id: str | None = Field(default=None, min_length=3, max_length=80)

    @field_validator("member_ids")
    @classmethod
    def unique_channel_members(cls, member_ids: list[str]) -> list[str]:
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("Channel members must be unique.")
        return member_ids


@dataclass
class MemberProjection:
    member_id: str
    name: str = ""
    coach_name: str = ""
    role: ProgramRole | None = None
    crucible_id: str = ""
    coach_id: str | None = None
    captain_id: str | None = None
    season_plan: dict[str, Any] | None = None
    calibrations: list[dict[str, Any]] = field(default_factory=list)
    reviews: dict[int, dict[str, Any]] = field(default_factory=dict)
    reopened_weeks: set[int] = field(default_factory=set)


class ReadModel:
    def __init__(self) -> None:
        self.members: dict[str, MemberProjection] = {}
        self.crucibles: dict[str, dict[str, Any]] = {}
        self.circles: dict[str, dict[str, Any]] = {}
        self.channels: dict[str, dict[str, Any]] = {}

    def member(self, member_id: str) -> MemberProjection:
        if member_id not in self.members:
            self.members[member_id] = MemberProjection(member_id=member_id)
        return self.members[member_id]

    def apply(self, event: DomainEvent) -> None:
        payload = event.payload
        if event.name == "CrucibleCreated":
            self.crucibles[payload["crucible_id"]] = payload
        elif event.name == "MemberEnrolledInCrucible":
            member = self.member(payload["member_id"])
            member.name = payload["name"]
            member.role = ProgramRole(payload["role"])
            member.crucible_id = payload["crucible_id"]
        elif event.name == "CoachAssignedToParticipant":
            participant = self.member(payload["member_id"])
            participant.coach_id = payload["mentor_id"]
            participant.coach_name = self.member(payload["mentor_id"]).name
        elif event.name == "CaptainAssignedToCoach":
            self.member(payload["member_id"]).captain_id = payload["mentor_id"]
        elif event.name == "CircleCreated":
            self.circles[payload["circle_id"]] = payload
        elif event.name == "ChannelCreated":
            self.channels[payload["channel_id"]] = payload
        elif event.name == "SeasonPlanSubmitted":
            self.member(payload["member_id"]).season_plan = payload
        elif event.name == "WeeklyCalibrationSubmitted":
            self.member(payload["member_id"]).calibrations.append(payload)
            self.member(payload["member_id"]).reopened_weeks.discard(payload["week"])
        elif event.name == "WeeklyCalibrationReviewed":
            self.member(payload["member_id"]).reviews[payload["week"]] = payload
        elif event.name == "WeeklyCalibrationReopened":
            self.member(payload["member_id"]).reopened_weeks.add(payload["week"])


class ApplicationService:
    def __init__(self, event_store: EventStore, read_model: ReadModel, clock: Callable[[], datetime] | None = None) -> None:
        self.event_store = event_store
        self.read_model = read_model
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _append(self, stream_id: str, command_id: str, name: str, payload: dict[str, Any]) -> list[DomainEvent]:
        version = sum(event.stream_id == stream_id for event in self.event_store.all())
        events = self.event_store.append(stream_id, version, command_id, [(name, payload)])
        for event in events:
            self.read_model.apply(event)
        return events

    def seed(self) -> None:
        if self.read_model.members:
            return
        self._append("crucible:demo-crucible", "seed-crucible", "CrucibleCreated", {
            "crucible_id": "demo-crucible", "name": "The Stewardship Season", "review_week_start": "2026-06-23", "refinement_week_start": "2026-06-30", "launch_date": "2026-07-07"
        })
        for member_id, name, role in [
            ("admin-amos", "Administrator Amos", ProgramRole.ADMINISTRATOR),
            ("captain-silas", "Captain Silas", ProgramRole.CAPTAIN),
            ("coach-elias", "Coach Elias", ProgramRole.COACH),
            ("demo-member", "Marcus", ProgramRole.PARTICIPANT),
        ]:
            self._append(f"member:{member_id}", f"seed-member-{member_id}", "MemberEnrolledInCrucible", {
                "crucible_id": "demo-crucible", "member_id": member_id, "name": name, "role": role.value
            })
        self._append("relationship:demo-member:coach", "seed-coach-assignment", "CoachAssignedToParticipant", {"crucible_id": "demo-crucible", "member_id": "demo-member", "mentor_id": "coach-elias"})
        self._append("relationship:coach-elias:captain", "seed-captain-assignment", "CaptainAssignedToCoach", {"crucible_id": "demo-crucible", "member_id": "coach-elias", "mentor_id": "captain-silas"})

    def create_crucible(self, command: CreateCrucibleCommand) -> dict[str, Any]:
        if command.crucible_id in self.read_model.crucibles:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Crucible already exists.")
        events = self._append(f"crucible:{command.crucible_id}", command.command_id, "CrucibleCreated", command.model_dump())
        return {"event_ids": [event.id for event in events], "crucible_id": command.crucible_id}

    def enroll_member(self, crucible_id: str, command: EnrollMemberCommand) -> dict[str, Any]:
        crucible = self.crucible_or_404(crucible_id)
        if command.member_id in self.read_model.members:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists in a Crucible.")
        payload = command.model_dump() | {"crucible_id": crucible["crucible_id"]}
        events = self._append(f"member:{command.member_id}", command.command_id, "MemberEnrolledInCrucible", payload)
        return {"event_ids": [event.id for event in events], "member_id": command.member_id}

    def assign_coach(self, crucible_id: str, command: AssignRelationshipCommand) -> dict[str, Any]:
        participant = self.member_in_crucible_or_404(command.member_id, crucible_id)
        coach = self.member_in_crucible_or_404(command.mentor_id, crucible_id)
        if participant.role != ProgramRole.PARTICIPANT or coach.role != ProgramRole.COACH:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Coach assignments require a participant and a Coach.")
        events = self._append(f"relationship:{command.member_id}:coach", command.command_id, "CoachAssignedToParticipant", command.model_dump() | {"crucible_id": crucible_id})
        return {"event_ids": [event.id for event in events], "status": "assigned"}

    def assign_captain(self, crucible_id: str, command: AssignRelationshipCommand) -> dict[str, Any]:
        coach = self.member_in_crucible_or_404(command.member_id, crucible_id)
        captain = self.member_in_crucible_or_404(command.mentor_id, crucible_id)
        if coach.role != ProgramRole.COACH or captain.role != ProgramRole.CAPTAIN:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Captain assignments require a Coach and a Captain.")
        events = self._append(f"relationship:{command.member_id}:captain", command.command_id, "CaptainAssignedToCoach", command.model_dump() | {"crucible_id": crucible_id})
        return {"event_ids": [event.id for event in events], "status": "assigned"}

    def create_circle(self, crucible_id: str, command: CreateCircleCommand) -> dict[str, Any]:
        self.crucible_or_404(crucible_id)
        if command.circle_id in self.read_model.circles:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Circle already exists.")
        expected_size = {CircleType.BUDDY: 2, CircleType.TRIAD: 3}.get(command.kind)
        if expected_size is not None and len(command.member_ids) != expected_size:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{command.kind.value} circles require exactly {expected_size} members.")
        for member_id in command.member_ids:
            self.member_in_crucible_or_404(member_id, crucible_id)
        if command.coach_sponsor_id is not None:
            sponsor = self.member_in_crucible_or_404(command.coach_sponsor_id, crucible_id)
            if sponsor.role != ProgramRole.COACH:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A circle sponsor must be a Coach.")
        payload = command.model_dump() | {"crucible_id": crucible_id}
        events = self._append(f"circle:{command.circle_id}", command.command_id, "CircleCreated", payload)
        return {"event_ids": [event.id for event in events], "circle_id": command.circle_id}

    def create_channel(self, crucible_id: str, command: CreateChannelCommand) -> dict[str, Any]:
        crucible = self.crucible_or_404(crucible_id)
        if command.channel_id in self.read_model.channels:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Channel already exists.")
        for member_id in command.member_ids:
            self.member_in_crucible_or_404(member_id, crucible_id)
        if command.kind == ChannelType.WHOLE_CRUCIBLE:
            expected_members = {member_id for member_id, member in self.read_model.members.items() if member.crucible_id == crucible_id}
            if set(command.member_ids) != expected_members:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A whole-Crucible channel must include every enrolled member.")
        if command.circle_id is not None:
            circle = self.read_model.circles.get(command.circle_id)
            if circle is None or circle["crucible_id"] != crucible_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Channel circle must belong to this Crucible.")
            expected_members = set(circle["member_ids"])
            if circle["coach_sponsor_id"] is not None:
                expected_members.add(circle["coach_sponsor_id"])
            if set(command.member_ids) != expected_members:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Circle channel membership must match the circle and its Coach sponsor.")
        if command.kind == ChannelType.PARTICIPANT_PRIVATE:
            if any(self.member_or_404(member_id).role != ProgramRole.PARTICIPANT for member_id in command.member_ids):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Participant-private channels cannot include Coaches or Captains.")
        payload = command.model_dump() | {"crucible_id": crucible["crucible_id"]}
        events = self._append(f"channel:{command.channel_id}", command.command_id, "ChannelCreated", payload)
        return {"event_ids": [event.id for event in events], "channel_id": command.channel_id}

    def submit_plan(self, command: SeasonPlanCommand) -> dict[str, Any]:
        self.member_or_404(command.member_id)
        payload = command.model_dump()
        payload["status"] = "submitted"
        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
        payload["template"] = season_plan_template()
        events = self._append(f"season-plan:{command.member_id}", command.command_id, "SeasonPlanSubmitted", payload)
        return {"event_ids": [event.id for event in events], "status": "submitted"}

    def submit_calibration(self, command: CalibrationCommand) -> dict[str, Any]:
        replayed = self.event_store.events_for_command(command.command_id)
        if replayed:
            return {"event_ids": [event.id for event in replayed], "status": "submitted"}
        member = self.member_or_404(command.member_id)
        if member.season_plan is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A Season Plan must be submitted before a weekly calibration.")
        if any(item["week"] == command.week for item in member.calibrations) and command.week not in member.reopened_weeks:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This week is already submitted. A Coach must reopen it before revision.")
        plan_values = member.season_plan["values"]
        if command.value_in_focus not in plan_values or command.value_most_neglected not in plan_values:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Weekly values must be selected from the Season Plan.")
        if command.value_in_focus == command.value_most_neglected:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Choose different values for most in focus and most neglected.")
        if command.role_to_forge not in member.season_plan["roles"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The role to forge must be selected from the Season Plan.")
        payload = command.model_dump()
        payload["status"] = "submitted"
        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
        payload["template"] = calibration_template()
        events = self._append(f"calibration:{command.member_id}:{command.week}", command.command_id, "WeeklyCalibrationSubmitted", payload)
        return {"event_ids": [event.id for event in events], "status": "submitted"}

    def review_calibration(self, member_id: str, week: int, command: CoachReviewCommand) -> dict[str, Any]:
        member = self.member_or_404(member_id)
        coach = self.member_or_404(command.coach_id)
        if (
            member.role != ProgramRole.PARTICIPANT
            or coach.role != ProgramRole.COACH
            or member.coach_id != command.coach_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach is not assigned to this participant.")
        if not any(item["week"] == week for item in member.calibrations):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weekly calibration not found.")
        payload = command.model_dump() | {"member_id": member_id, "week": week, "reviewed_at": datetime.now(timezone.utc).isoformat()}
        events = self._append(f"review:{member_id}:{week}", command.command_id, "WeeklyCalibrationReviewed", payload)
        return {"event_ids": [event.id for event in events], "status": "revision_requested" if command.request_revision else "reviewed"}

    def reopen_calibration(self, member_id: str, week: int, command: ReopenCalibrationCommand) -> dict[str, Any]:
        member = self.member_or_404(member_id)
        coach = self.member_or_404(command.coach_id)
        if (
            member.role != ProgramRole.PARTICIPANT
            or coach.role != ProgramRole.COACH
            or member.coach_id != command.coach_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach is not assigned to this participant.")
        if not any(item["week"] == week for item in member.calibrations):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weekly calibration not found.")
        if week in member.reopened_weeks:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This week is already reopened.")
        payload = command.model_dump() | {"member_id": member_id, "week": week, "reopened_at": datetime.now(timezone.utc).isoformat()}
        events = self._append(f"reopen:{member_id}:{week}", command.command_id, "WeeklyCalibrationReopened", payload)
        return {"event_ids": [event.id for event in events], "status": "reopened"}

    def weekly_due_states(self, member_id: str) -> dict[str, Any]:
        member = self.member_or_404(member_id)
        if member.role != ProgramRole.PARTICIPANT:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Weekly due-state is defined for participants.")
        crucible = self.crucible_or_404(member.crucible_id)
        launch = date.fromisoformat(crucible["launch_date"])
        now = self._clock()
        today = now.date()
        elapsed_days = (today - launch).days
        current_week = min(max(elapsed_days // 7 + 1, 0), SEASON_WEEKS) if elapsed_days >= 0 else 0
        submitted_weeks = {item["week"] for item in member.calibrations}
        tracked_weeks = submitted_weeks | set(member.reviews) | member.reopened_weeks
        last_week = min(max([current_week, *tracked_weeks]) if (current_week or tracked_weeks) else 0, SEASON_WEEKS)
        weeks: list[dict[str, Any]] = []
        for week in range(1, last_week + 1):
            opens_on = launch + timedelta(days=7 * (week - 1))
            due_on = launch + timedelta(days=7 * week)
            reopened = week in member.reopened_weeks
            reviewed = week in member.reviews and not reopened
            submitted = week in submitted_weeks and not reopened
            if reviewed:
                state = "reviewed"
            elif submitted:
                state = "submitted"
            elif today > due_on:
                state = "overdue"
            elif (due_on - today).days <= DUE_SOON_DAYS:
                state = "due_soon"
            else:
                state = "opened"
            weeks.append({
                "week": week,
                "opens_on": opens_on.isoformat(),
                "due_on": due_on.isoformat(),
                "state": state,
                "submitted": submitted,
                "reviewed": reviewed,
                "reopened": reopened,
            })
        counts = {state: sum(item["state"] == state for item in weeks) for state in DUE_STATES}
        return {
            "member_id": member.member_id,
            "generated_at": now.isoformat(),
            "current_week": current_week,
            "weeks": weeks,
            "counts": counts,
        }

    def dashboard(self, member_id: str) -> dict[str, Any]:
        member = self.member_or_404(member_id)
        latest = member.calibrations[-1] if member.calibrations else None
        reopened_weeks = sorted(member.reopened_weeks)
        if reopened_weeks:
            current_week = reopened_weeks[-1]
        elif latest and latest["week"] < 12:
            current_week = latest["week"] + 1
        else:
            current_week = latest["week"] if latest else 1
        direct_reports = [
            {"member_id": candidate.member_id, "name": candidate.name, "role": candidate.role.value if candidate.role else None}
            for candidate in self.read_model.members.values()
            if (member.role == ProgramRole.COACH and candidate.coach_id == member_id)
            or (member.role == ProgramRole.CAPTAIN and candidate.captain_id == member_id)
        ]
        return {
            "member_id": member.member_id,
            "name": member.name,
            "role": member.role.value if member.role else None,
            "coach_name": member.coach_name,
            "season_plan": member.season_plan,
            "latest_calibration": latest,
            "latest_review": member.reviews.get(latest["week"]) if latest else None,
            "current_week": current_week,
            "calibration_count": len(member.calibrations),
            "reopened_weeks": reopened_weeks,
            "weekly_due": self.weekly_due_states(member_id) if member.role == ProgramRole.PARTICIPANT else None,
            "direct_reports": direct_reports,
        }

    def development_accounts(self) -> list[dict[str, str]]:
        return [
            {"member_id": member.member_id, "name": member.name, "role": member.role.value}
            for member in self.read_model.members.values() if member.role is not None
        ]

    def coach_participant_record(self, coach_id: str, participant_id: str) -> dict[str, Any]:
        coach = self.member_or_404(coach_id)
        participant = self.member_or_404(participant_id)
        if coach.role != ProgramRole.COACH or participant.coach_id != coach_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach is not assigned to this participant.")
        return {"participant": self.dashboard(participant_id)}

    def captain_coach_status(self, captain_id: str, coach_id: str) -> dict[str, Any]:
        captain = self.member_or_404(captain_id)
        coach = self.member_or_404(coach_id)
        if (
            captain.role != ProgramRole.CAPTAIN
            or coach.role != ProgramRole.COACH
            or coach.captain_id != captain_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Captain is not assigned to this Coach.")

        participants = []
        for participant in self.read_model.members.values():
            if participant.coach_id != coach_id:
                continue
            latest = participant.calibrations[-1] if participant.calibrations else None
            review = participant.reviews.get(latest["week"]) if latest else None
            review_status = (
                "revision_requested" if review and review["request_revision"]
                else "reviewed" if review
                else "awaiting_review" if latest
                else "not_submitted"
            )
            participants.append({
                "member_id": participant.member_id,
                "name": participant.name,
                "season_plan_status": "submitted" if participant.season_plan else "not_submitted",
                "calibration": {"week": latest["week"], "review_status": review_status} if latest else None,
            })
        return {
            "coach": {"member_id": coach.member_id, "name": coach.name},
            "summary": {
                "participant_count": len(participants),
                "plans_submitted": sum(item["season_plan_status"] == "submitted" for item in participants),
                "calibrations_submitted": sum(item["calibration"] is not None for item in participants),
                "calibrations_reviewed": sum(item["calibration"] is not None and item["calibration"]["review_status"] != "awaiting_review" for item in participants),
            },
            "participants": participants,
        }

    def member_or_404(self, member_id: str) -> MemberProjection:
        if member_id not in self.read_model.members:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
        return self.read_model.members[member_id]

    def crucible_or_404(self, crucible_id: str) -> dict[str, Any]:
        if crucible_id not in self.read_model.crucibles:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crucible not found.")
        return self.read_model.crucibles[crucible_id]

    def member_in_crucible_or_404(self, member_id: str, crucible_id: str) -> MemberProjection:
        member = self.member_or_404(member_id)
        if member.crucible_id != crucible_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Member is not enrolled in this Crucible.")
        return member

    def crucible_detail(self, crucible_id: str) -> dict[str, Any]:
        crucible = self.crucible_or_404(crucible_id)
        members = [
            {"member_id": member.member_id, "name": member.name, "role": member.role.value if member.role else None, "coach_id": member.coach_id, "captain_id": member.captain_id}
            for member in self.read_model.members.values() if member.crucible_id == crucible_id
        ]
        circles = [circle for circle in self.read_model.circles.values() if circle["crucible_id"] == crucible_id]
        channels = [channel for channel in self.read_model.channels.values() if channel["crucible_id"] == crucible_id]
        return {"crucible": crucible, "members": members, "circles": circles, "channels": channels}


def create_app(development_mode: bool | None = None, clock: Callable[[], datetime] | None = None) -> FastAPI:
    app = FastAPI(title="3F API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
    service = ApplicationService(EventStore(), ReadModel(), clock=clock)
    service.seed()
    app.state.service = service
    app.state.development_mode = development_mode if development_mode is not None else os.getenv("THREEF_DEVELOPMENT_MODE", "true").lower() == "true"

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/reference/scales")
    def scales() -> dict[str, Any]:
        return scale_definitions()

    @app.get("/api/reference/templates")
    def templates() -> dict[str, Any]:
        return template_catalog()

    @app.get("/api/dashboard/{member_id}")
    def dashboard(member_id: str) -> dict[str, Any]:
        return service.dashboard(member_id)

    @app.get("/api/participants/{member_id}/weekly-due-state")
    def weekly_due_state(member_id: str) -> dict[str, Any]:
        return service.weekly_due_states(member_id)

    @app.get("/api/development/accounts")
    def development_accounts() -> list[dict[str, str]]:
        if not app.state.development_mode:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
        return service.development_accounts()

    @app.get("/api/coaches/{coach_id}/participants/{participant_id}")
    def coach_participant_record(coach_id: str, participant_id: str) -> dict[str, Any]:
        return service.coach_participant_record(coach_id, participant_id)

    @app.get("/api/captains/{captain_id}/coaches/{coach_id}/status")
    def captain_coach_status(captain_id: str, coach_id: str) -> dict[str, Any]:
        return service.captain_coach_status(captain_id, coach_id)

    @app.post("/api/crucibles", status_code=status.HTTP_201_CREATED)
    def create_crucible(command: CreateCrucibleCommand) -> dict[str, Any]:
        return service.create_crucible(command)

    @app.get("/api/crucibles/{crucible_id}")
    def crucible_detail(crucible_id: str) -> dict[str, Any]:
        return service.crucible_detail(crucible_id)

    @app.post("/api/crucibles/{crucible_id}/members", status_code=status.HTTP_201_CREATED)
    def enroll_member(crucible_id: str, command: EnrollMemberCommand) -> dict[str, Any]:
        return service.enroll_member(crucible_id, command)

    @app.post("/api/crucibles/{crucible_id}/coach-assignments", status_code=status.HTTP_201_CREATED)
    def assign_coach(crucible_id: str, command: AssignRelationshipCommand) -> dict[str, Any]:
        return service.assign_coach(crucible_id, command)

    @app.post("/api/crucibles/{crucible_id}/captain-assignments", status_code=status.HTTP_201_CREATED)
    def assign_captain(crucible_id: str, command: AssignRelationshipCommand) -> dict[str, Any]:
        return service.assign_captain(crucible_id, command)

    @app.post("/api/crucibles/{crucible_id}/circles", status_code=status.HTTP_201_CREATED)
    def create_circle(crucible_id: str, command: CreateCircleCommand) -> dict[str, Any]:
        return service.create_circle(crucible_id, command)

    @app.post("/api/crucibles/{crucible_id}/channels", status_code=status.HTTP_201_CREATED)
    def create_channel(crucible_id: str, command: CreateChannelCommand) -> dict[str, Any]:
        return service.create_channel(crucible_id, command)

    @app.post("/api/season-plans", status_code=status.HTTP_201_CREATED)
    def submit_plan(command: SeasonPlanCommand) -> dict[str, Any]:
        return service.submit_plan(command)

    @app.post("/api/calibrations", status_code=status.HTTP_201_CREATED)
    def submit_calibration(command: CalibrationCommand) -> dict[str, Any]:
        return service.submit_calibration(command)

    @app.post("/api/calibrations/{member_id}/{week}/review", status_code=status.HTTP_201_CREATED)
    def review_calibration(member_id: str, week: int, command: CoachReviewCommand) -> dict[str, Any]:
        return service.review_calibration(member_id, week, command)

    @app.post("/api/calibrations/{member_id}/{week}/reopen", status_code=status.HTTP_201_CREATED)
    def reopen_calibration(member_id: str, week: int, command: ReopenCalibrationCommand) -> dict[str, Any]:
        return service.reopen_calibration(member_id, week, command)

    @app.get("/api/events")
    def events() -> list[dict[str, Any]]:
        return [asdict(event) for event in service.event_store.all()]

    return app


app = create_app()
