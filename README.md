# 3F App

> **MVP motto: Ship fast and adjust quickly.**

3F App is an offline-first coaching platform for men practicing a 12-week season of stewardship. It replaces disconnected email and WhatsApp workflows with one reliable operating system for season design, weekly calibration, accountable relationships, Coach review, and approved framework knowledge.

The first release validates one outcome: participants complete an honest weekly calibration, Coaches respond at the right time, and a Crucible can operate its full 12-week cycle from one platform.

## Run Locally

The standard development and review environment is Docker Compose. It starts the API and PWA with source mounts and hot reload.

```bash
cd ~/3f-app
docker compose up --build
```

Open the PWA at `http://localhost:5173`. The API and its OpenAPI documentation are available at `http://localhost:8000` and `http://localhost:8000/docs`.

Use `docker compose down` to stop the stack. Use `docker compose down -v` only when you deliberately want to reset the container dependency volumes.

Python dependencies, the virtual environment, locking, tests, and API commands use [uv](https://docs.astral.sh/uv/). Do not use `pip` for this project. Container development runs `uv` inside the `api` service; direct WSL commands remain available when needed:

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run uvicorn threef.app:app --app-dir src --reload
```

The local API seeds a participant named Marcus at `demo-member`. Build the browser bundle outside Docker with `cd web && npm run build`.

### Autonomous Delivery Loop

`TODO.md` is the prioritized execution backlog. The Ralph loop runs OpenCode against one highest-priority TODO item per iteration, requires verification and a Conventional Commit, pushes each session's commits to `origin`, and stops on completion of every backlog item, a documented blocker, or an iteration limit.

```bash
cd ~/3f-app
./ralph-loop.sh
```

Useful controls:

```bash
# Run at most three iterations.
RALPH_MAX_ITERATIONS=3 ./ralph-loop.sh

# Select a specific OpenCode model or agent.
RALPH_MODEL="provider/model" RALPH_AGENT="agent-name" ./ralph-loop.sh

# Permit unattended OpenCode tool approvals. Review the prompt and worktree first.
RALPH_AUTO_APPROVE=1 ./ralph-loop.sh
```

Iteration logs are written to `ralph/runs/` and ignored by Git. Read `ralph/PROMPT.md` before changing the loop contract.

### Development Account Switcher

The Compose development environment sets `THREEF_DEVELOPMENT_MODE=true`. The PWA then displays a local-only account switcher for the seeded Participant, Coach, Captain, and Administrator accounts. It is intended solely for reviewing role-specific UI while authentication is not yet implemented.

Set `THREEF_DEVELOPMENT_MODE=false` outside development. This disables the `/api/development/accounts` endpoint and removes the switcher from a production browser build.

### Development Administrator Setup

Select **Administrator Amos** from the development account switcher, then open **Setup**. The local-only workspace creates a Crucible, enrolls its members, creates Coach or Captain assignments, and creates circles and channels through the same API commands used by the application. It keeps each action explicit so the API validates the required membership and relationship boundaries.

Create a Crucible before enrolling members. Create all members before assignments, circles, or channels. Circle channels must exactly match the circle members and optional Coach sponsor; participant-private channels may contain Participants only.

### Participant Review Feedback

The participant Anvil shows the latest feedback from the assigned Coach. A revision request is presented separately with its next action: review the feedback and prepare the revision. The submitted week remains immutable until the assigned Coach reopens it; reopening is a separate workflow so submission history is preserved. When the Coach reopens a week, the participant dashboard points at that week and announces that the earlier submission is preserved and ready to revise. In Coach review, the Coach submits feedback or a revision request, then explicitly reopens the submitted week using the same feedback as the reopen reason.

## The Why

Most men do not lack effort. They lack a way to measure themselves honestly.

Modern life permits drift without immediate consequence. A man can avoid, numb, delay, overwork, or appear competent while remaining internally misaligned. The platform does not add more hype, content, or productivity pressure. It provides a structured internal readout.

The work is **orientation before optimization**.

> A man without a scale guesses. A man with a scale adjusts.

## The Standard: Clean Burn

The standard is not perfection, intensity, public performance, or constant achievement.

> **Clean burn.**

Clean burn is the practice of reducing internal buildup that distorts judgment, drains energy, and makes disciplined action unnecessarily difficult. It asks a man to identify what he is feeding, holding, releasing, and deliberately shaping.

> You do not earn clarity. You clear for it.

### The Slag Channel

Every furnace creates waste. In a man, that buildup can be resentment replayed but never resolved, jealousy masked as indifference, guilt from commitments not kept, avoidance presented as busyness, or self-deception used to preserve comfort.

The product uses the **Slag Channel** to name this buildup without shame or diagnosis. A low read does not make a man a failure. It signals that release, support, simplification, or honest confrontation may be more useful than applying more pressure.

The operating method is simple:

1. **Measure correctly.** Locate actual operating conditions, not a preferred self-image.
2. **Tell the truth.** Name the evidence without stories, blame, or exaggeration.
3. **Adjust deliberately.** Take a bounded next action rather than attempting a total reset.

> Read your system. Tell the truth. Then strike where it matters.

## Product Principles

1. Weekly practice comes first. Every screen helps a member prepare, submit, review, or act on a weekly calibration.
2. Mobile and offline are requirements. A weekly calibration must work on a phone with unreliable or unavailable connectivity.
3. Human coaching remains accountable. AI is an approved-framework guide, not a replacement for a Coach.
4. Privacy follows relationship boundaries. Members only see their own private data and authorized conversations.
5. Configuration beats code. Templates, due dates, reminders, and Crucible dates must be configurable.
6. Accuracy over performance. No leaderboards, streaks, public rankings, or simplistic performance scores.
7. Ship fast and adjust quickly. Use real Crucibles as the product laboratory; release small, useful changes frequently.

## People And Relationships

### Roles

| Role          | Responsibilities                                                               | Access                                                             |
| ------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Participant   | Build and live a season plan; complete weekly reads; engage in accountability. | Own plans, check-ins, Coach feedback, and authorized channels.     |
| Coach         | Guide assigned participants with timely, concrete review.                      | Assigned participants and sponsored group channels.                |
| Captain       | Mentor Coaches and protect coaching quality.                                   | Assigned Coaches, Captain spaces, and Coach review status.         |
| Administrator | Operate the program and configure its framework.                               | Users, Crucibles, templates, assignments, knowledge, and policies. |

### Crucibles And Channels

A **Crucible** is an organized 12-week cycle. Members may be organized into small groups, buddy pairs, or triads. Coaches are assigned to participants; Captains are assigned to Coaches.

Required channel types:

- Whole Crucible.
- Small group, including its Coach sponsor.
- Buddy pair.
- Triad.
- Coach-to-participant direct channel.
- Captain-to-Coach direct channel.
- Coach and Captain leadership channels.
- Participant-created private channels, without Coach or Captain visibility unless the members explicitly invite them.

Channel membership is explicit. Global role alone never grants access to private conversations or assessments.

## The 12-Week Season Design Journey

The season plan is the baseline for a Crucible. It is a stewardship plan, not a productivity plan. Participants build containers around priorities, protect those containers, and act consistently inside them.

The opening question is:

> What areas of my life need intentional stewardship for the next 12 weeks?

### Crucible Timeline

Every Crucible configures these phases rather than hard-coding dates:

| Phase           | Purpose                                                                     |
| --------------- | --------------------------------------------------------------------------- |
| Review Week     | Review current reality, unfinished commitments, and important life domains. |
| Refinement Week | Clarify, simplify, and make the plan realistic before Coach review.         |
| 12-Week Season  | Execute, calibrate weekly, review, and adjust.                              |

For the initial season, the target dates are:

- Review Week: week of June 23.
- Refinement Week: week of June 30.
- Launch: week of July 7.

### Season Design Steps

1. **Name life domains.** Select only the domains that truly matter this season. Suggested domains include health, marriage, family, faith, work, finances, home, leadership, friendships, personal development, recovery and restoration, business growth, spiritual formation, and physical environment. Custom domains are permitted.
2. **Define current reality.** For every selected domain: "Right now, this area is..." Statements must be factual and grounded, without shame, blame, or exaggeration.
3. **Define the 12-week outcome.** For every domain: "By the end of this 12-week season, I will have..." Outcomes must be realistic, measurable, and connected to the domain.
4. **Build the container.** Define protected time, action within it, its boundary, what will be removed or reduced, and evidence that it works.
5. **Choose weekly actions.** Select one to three visible, trackable actions for each domain: "Each week, I will..."
6. **Identify what must be eliminated.** Record commitments to pause, delegate, finish, drop, or reduce. This is required so a season is not built on top of an overloaded life.
7. **Create the weekly scoreboard.** Establish simple measures for each domain. Each week they are recorded as Green (completed), Yellow (partially completed), or Red (missed or avoided). This is awareness, not punishment.
8. **Set the weekly review rhythm.** Choose a repeated day, time, timezone, duration, and reminder timing.
9. **Name the season.** The name describes the kind of man the participant is becoming, such as "The Stewardship Season" or "The Consistency Season."
10. **Submit for Coach review.** The in-app Season Plan is the source of truth. PDF export may be added later; external documents are not required.

### Coach And Captain Review

The Coach can approve a season plan or request a focused revision. Coaches cannot rewrite a participant's plan; the participant owns and resubmits it. Reviews may flag overload, vague outcomes, missing containers, missing elimination commitments, or unmeasurable scoreboards.

Captains use the same season structure with their assigned Coaches. They mentor Coach development and review Coach completion and quality, not participant private content unless separately assigned.

## Weekly Calibration: The 3F System Read

The weekly check-in is not generic journaling. It is a structured calibration that converts lived experience into a clear operating read.

It asks:

- What did I feed the fire?
- What did I fail to release?
- What did I actually carry and shape?

The participant sees their season name, active domains, outcomes, protected containers, weekly actions, last week's strikes, and current submission status before beginning the read.

### 1. Aim: The Furnace Stack

Aim is the structure a life burns inside.

The participant records:

- Current aim: what am I building my life toward, and what direction am I choosing to hold even when it is hard?
- A Momentum Scale (Furnace Read) level.
- Evidence for what created that level during the week.

The previous aim carries forward so the participant can confirm, refine, or replace it without needless rewrites.

### 2. Meaning: The Hearth

Meaning is what actually carried weight.

The participant records one moment that mattered and why it mattered. If nothing stands out, the participant records where he felt numb, distracted, or disconnected. The app does not label this as failure or attempt clinical interpretation.

### 3. Values: The Refractory Lining

Values are demonstrated by what is protected under pressure.

The participant ranks core values in the order they were actually lived that week, identifies values expressed or compromised, and records supporting evidence. Declared values from the season plan remain intact; each weekly ranking is a historical snapshot.

### 4. Responsibility: The Anvil

Responsibility is the ability to consistently hold and shape an actual load.

For each active role, such as man, father, partner, builder, or leader, the participant records a Responsibility Scale (Forge Read) level and an evidence statement.

> No stories. Just weight and truth.

Roles originate in the season plan and can be marked inactive with an explanation, preserving history.

### 5. Friction: The Slag Channel

Friction is internal resistance and unreleased buildup. The purpose is exposure, not immediate fixing.

The participant records:

- What did I avoid?
- What drained me more than it should have?
- What am I still carrying that has not been released?

Entries can optionally link to a season domain, role, container, or action. The MVP does not prescribe automated solutions.

### 6. Cultivation: The Hammer

Cultivation turns an accurate read into focused action.

The participant chooses one role to deliberately strengthen and creates up to three measurable, repeatable strikes for the next week. There is no fourth strike. The first strike is designated as the most important action for the next seven days.

Previous strikes pre-populate the following weekly read so the participant records whether each was completed, partially completed, missed, or not applicable.

### Season Plan Integration

The season plan provides strategic context; the 3F System Read is the weekly operating layer.

| Season Plan             | Weekly Calibration                                             |
| ----------------------- | -------------------------------------------------------------- |
| Season name             | Always visible in the read.                                    |
| Domains and outcomes    | Available context and optional links for friction and strikes. |
| Protected containers    | Recorded as held, partially held, or broken.                   |
| Weekly actions          | Updated through the Green/Yellow/Red scoreboard.               |
| Elimination commitments | Recorded as progress, stalled, or avoided.                     |
| Review rhythm           | Schedules weekly calibration reminders.                        |

## Diagnostic Scales

The scales are diagnostic coordinates, not motivational scores, outcomes, or identity judgments. Each assessment stores a numeric value, label, exact definition, evidence statement, and template version. The UI favors named states over bare numbers.

### Momentum Scale: Furnace Read

**Measures:** Internal flow versus internal buildup, not speed or output.

| Level | Label         | Definition                                                                                                                   |
| ----: | ------------- | ---------------------------------------------------------------------------------------------------------------------------- |
|     1 | Clogged       | I feel backed up with thoughts and emotions I have not faced; everything in me feels heavy, slow, and resistant to movement. |
|     2 | Toxic         | I notice resentment, envy, or frustration leaking into everything; my fire burns dirty and distorts how I see things.        |
|     3 | Pressurized   | I am holding in too much; I have not released what is building, and it is starting to affect my focus and reactions.         |
|     4 | Leaking       | I let some pressure out, but inconsistently; I vent in unproductive ways and still carry lingering weight.                   |
|     5 | Ventilating   | I am starting to release what I carry in healthier ways; my mind clears in moments, but buildup still returns.               |
|     6 | Clearing      | I actively face and process what has been sitting in me; my energy feels lighter and more usable.                            |
|     7 | Flowing       | I release tension as it arises; I do not let things sit long enough to distort my direction.                                 |
|     8 | Refined       | I convert pressure into clarity quickly; what once clogged me now fuels me with precision.                                   |
|     9 | Clean-Burning | I operate with minimal internal waste; my energy moves freely, and my fire runs strong, steady, and true.                    |

Required follow-up: **What specifically created that level this week?**

### Responsibility Scale: Forge Read

**Measures:** How stably the participant holds and shapes the load he carries, not how much he carries.

| Level | Label       | Definition                                                                                                       |
| ----: | ----------- | ---------------------------------------------------------------------------------------------------------------- |
|     1 | Crushed     | I have taken on more than I can hold; without structure, everything feels like it is collapsing on me.           |
|     2 | Fractured   | I am trying to carry my responsibilities, but without consistency; things slip, and I feel scattered.            |
|     3 | Unstable    | I show up inconsistently; I handle some responsibilities well, but others fall through due to lack of structure. |
|     4 | Holding     | I meet my core responsibilities; I am stable, but I have not built strength beyond maintaining.                  |
|     5 | Set         | I have created basic structure; I can rely on myself to handle what is in front of me without major failure.     |
|     6 | Grounded    | I handle pressure with growing consistency; my routines support me, even when things get heavy.                  |
|     7 | Structured  | I have built a reliable system; I do not just react, I operate with intention across my roles.                   |
|     8 | Forging     | I use responsibility to shape myself; pressure strengthens me instead of wearing me down.                        |
|     9 | Unbreakable | I carry weight with precision and control; no matter the load, I remain stable, effective, and sharp.            |

Required follow-up for every role: **What actually happened that justifies this rating?**

## PWA And Offline-First Requirements

3F App is a mobile-first Progressive Web App. It must be installable and functional for active work without an internet connection.

- Provide a web app manifest, service worker, offline app shell, and mobile-first navigation.
- Store only authorized active-program content, drafts, pending actions, and sync metadata locally in encrypted browser storage.
- Write user commands locally first through a durable outbox with client-generated IDs, expected stream versions, retries, and idempotency.
- Synchronize queued commands and authorized projections on reconnection.
- Show clear states: local draft, synchronizing, synchronized, or needs attention.
- Expose an Outbox screen that lists every queued command with its state (waiting for connection, synchronizing, or needs attention), offers per-command and whole-outbox retry, and lets a confirmed conflict be discarded.
- Preserve conflicts rather than silently overwriting them. Formal submissions are immutable unless a Coach reopens them.
- Queue offline messages and show sending, sent, or needs-attention status.
- Clear local data on logout; do not put sensitive information in URLs, unauthenticated caches, or push payloads.

## Notifications

Notifications are Web Push notifications delivered through the PWA service worker, with an in-app notification center as a fallback.

Notification types:

- Review Week and Refinement Week start/deadline reminders.
- Season plan revision and approval notices.
- Weekly calibration open, due-soon, and overdue reminders.
- Weekly review rhythm reminders.
- New Coach, Captain, or authorized channel messages.
- Submitted check-in and review-workflow notifications.

Notification policy:

- Push is explicitly opt-in and managed per device.
- Delivery is evaluated server-side at send time using the member's IANA timezone.
- Quiet hours are **off by default**. A member may opt in, choosing days, start/end time, and suppression or digest behavior.
- Members can mute individual channels, groups, or conversations permanently or until a chosen time.
- Group and channel mutes apply to social-message alerts, not required season-plan, calibration, or review-workflow notices.
- Push payloads remain generic by default to avoid exposing private coaching information on a locked device.
- iPhone and iPad push requires a Home Screen-installed PWA on supported iOS versions; the platform never treats push as guaranteed delivery.

## AI Assistant

The client assistant is an approved-framework guide. It uses only published, authorized knowledge from the 3F glossary.

It can:

- Explain framework language, scales, principles, and practices.
- Ask orienting questions grounded in approved knowledge.
- Help a member prepare a concise question for a Coach.
- Escalate a member request to their assigned Coach.

It cannot:

- Diagnose mental health conditions or assign a member's scale level.
- Infer character, risk, intent, or certainty from check-in data.
- Replace Coach judgment or autonomously coach a participant.
- Access or reveal data outside the member's authorization boundary.

AI interactions retain an audit record of prompt version, retrieved knowledge IDs, output, and escalation action. Human-approved Coach-facing summaries and automation agents are deferred until the core workflow produces enough evidence to evaluate them safely.

## Technical Architecture

### Stack

- **Frontend:** TypeScript and React PWA.
- **Backend:** Python, FastAPI, Pydantic, strict typing.
- **Local adapters:** in-memory event store, projection store, notification sink, clock, identity claims, and AI stub.
- **Production adapters:** AWS Lambda, API Gateway, DynamoDB, DynamoDB Streams, EventBridge, Cognito, S3, and a managed LLM provider behind an application port.

### Architecture Style

Use Onion architecture with strict dependency direction:

```text
domain/          Entities, value objects, policies, domain events
application/     Commands, queries, handlers, projections, authorization use cases
ports/           Event store, repositories, clock, notification, AI, identity interfaces
infrastructure/  DynamoDB, EventBridge, Cognito, Web Push, AWS and local adapters
api/             Typed HTTP request/response models and composition root
```

Keep domain behavior framework-independent. Prefer immutable value objects and functional transformations near the infrastructure boundary.

### Event-Sourced, Event-Driven Core

The source of truth is append-only, versioned event streams. Read models are asynchronous projections optimized for dashboards, queues, reminders, synchronization, and authorization lookups. Command writes use optimistic concurrency and idempotency to prevent silent overwrite.

Representative events:

- `CrucibleCreated`
- `MemberEnrolledInCrucible`
- `CoachAssignedToParticipant`
- `CaptainAssignedToCoach`
- `SeasonDesignStarted`
- `SeasonPlanSubmitted`
- `SeasonPlanApproved`
- `SeasonPlanRevisionRequested`
- `WeeklyCalibrationOpened`
- `MomentumAssessed`
- `RoleResponsibilityRated`
- `FrictionExposed`
- `DeliberateStrikeCommitted`
- `WeeklyCalibrationSubmitted`
- `WeeklyCalibrationReviewed`
- `WeeklyCalibrationReopened`
- `ChannelMembershipGranted`
- `ChannelMessagePosted`
- `ChannelRead`
- `NotificationPreferenceChanged`
- `NotificationScheduled`
- `NotificationSuppressed`
- `ClientCommandSynchronized`
- `SynchronizationConflictDetected`

## Privacy And Safety

- Encrypt data in transit and at rest.
- Keep check-in and assessment content out of URLs, generic analytics, logs, and detailed push previews.
- Audit sensitive access, submission, review, AI, and notification actions.
- Use application-level relationship authorization, not global roles alone.
- Provide account/device session management and retention/deletion controls before the pilot.
- The product is general membership software, not a regulated health or therapy platform. It must not imply therapy, diagnosis, or crisis intervention.

## MVP Delivery Plan

### Milestone 0: Product Foundation

Create the repository, CI, formatting/linting/type checking, test harness, architecture boundaries, local adapters, AWS deployment foundations, and seed data for a sample Crucible.

**Exit:** Developers can run the platform locally; CI runs the automated suite; a test user can authenticate with correct role claims.

### Milestone 1: Identity And Crucible Structure

Build user profiles, roles, Crucible dates, memberships, Coach/Captain assignments, small groups, buddies, triads, channels, and relationship authorization tests.

**Exit:** An administrator creates a pilot Crucible without engineering support; all private data and channel boundaries are enforced.

#### Current POC APIs

The local event-sourced API now supports the foundation of this milestone:

- `POST /api/crucibles` and `GET /api/crucibles/{crucible_id}` for a cycle and its operational projection.
- `POST /api/crucibles/{crucible_id}/members` to enroll a Participant, Coach, Captain, or Administrator.
- `POST /api/crucibles/{crucible_id}/coach-assignments` and `/captain-assignments` for reporting relationships.
- `POST /api/crucibles/{crucible_id}/circles` for small groups, buddy pairs, and triads, including an optional Coach sponsor.
- `POST /api/crucibles/{crucible_id}/channels` for explicit channel membership.
- `POST /api/season-plans`, `POST /api/calibrations`, and `POST /api/calibrations/{member_id}/{week}/review` for the participant submission and Coach review loop.
- `POST /api/calibrations/{member_id}/{week}/reopen` for an assigned Coach to reopen a submitted week for revision. Reopening is authorized by the Coach relationship, records a `WeeklyCalibrationReopened` event, and leaves the earlier submission in the append-only history.
- `GET /api/reference/templates` for the versioned Season Plan and weekly calibration templates, including prompt text and diagnostic scale definitions.
- `GET /api/reference/scales` for the Momentum (Furnace) and Responsibility (Forge) scale definitions.
- `GET /api/coaches/{coach_id}/participants/{participant_id}` for an assigned Coach's full submitted calibration record; unassigned relationships are rejected.
- `GET /api/captains/{captain_id}/coaches/{coach_id}/status` for an assigned Captain's Coach completion and review-state projection. It returns roster names, plan/submission/review state, and aggregate counts only, never participant calibration or feedback content.
- `GET /api/participants/{member_id}/weekly-due-state` for the participant's per-week operating state, also embedded as `weekly_due` in `GET /api/dashboard/{member_id}`.
- `GET /api/members/{member_id}/channels` for the channels a member explicitly belongs to, each with its message and unread counts.
- `GET /api/members/{member_id}/channels/{channel_id}/messages` for authorized thread history; channel membership is required.
- `POST /api/channels/{channel_id}/messages` to persist a channel message as a `ChannelMessagePosted` event.
- `POST /api/channels/{channel_id}/read` to advance the member's `ChannelRead` position and clear their unread count.

The POC validates that buddy pairs have two members, triads have three, Coach sponsors are Coaches in the same Crucible, circle channels match their circle membership, participant-private channels exclude Coaches and Captains, and Captain visibility is limited to assigned Coach status without participant calibration content.

Every Season Plan and weekly calibration submission stores a snapshot of the exact template version, prompts, and scale definitions used at submit time. Changing a template in a later release introduces a new version and does not rewrite the historical context of earlier submissions.

### Weekly Due-State Projection

`GET /api/participants/{member_id}/weekly-due-state` projects each opened week of the 12-week season as one of five operating states:

- **opened**: the week is open and not yet due soon.
- **due_soon**: the week's deadline falls within three days.
- **overdue**: the deadline passed without a submission.
- **submitted**: a calibration is recorded and awaits Coach review.
- **reviewed**: the assigned Coach has reviewed the submission.

A Coach reopening a week returns it to the participant's action queue (`opened`, `due_soon`, or `overdue`) and flags `reopened: true` while the earlier submission stays in the append-only history. Week deadlines derive from the Crucible `launch_date`, so a Crucible configures its own schedule rather than hard-coding dates. The participant Anvil renders this projection as a weekly schedule with the current due state.

### Versioned Templates

Season Plan and weekly calibration templates are versioned by `TEMPLATE_VERSION`. A submission embeds its template snapshot in the `SeasonPlanSubmitted` or `WeeklyCalibrationSubmitted` event, so a Coach reviewing old work sees the exact prompts and scale definitions the participant answered. The reference catalog is available at `GET /api/reference/templates`.

In the PWA, a Coach selects **Coach review** in the Anvil, opens an assigned participant's submitted calibration, sees each of the six 3F sections, then sends participant-visible feedback or requests a revision. The review is stored as a `WeeklyCalibrationReviewed` event.

### Authorized Text Channels

Text channels are explicit, membership-scoped conversations. A member can only list, read, or post in a channel whose `member_ids` include them and that belongs to their Crucible, so global role alone never grants access. Membership is set when the channel is created through `POST /api/crucibles/{crucible_id}/channels`.

Messages are durable `ChannelMessagePosted` events on the channel's append-only stream. `GET /api/members/{member_id}/channels` returns each authorized channel with its unread count and a last-message preview; `GET /api/members/{member_id}/channels/{channel_id}/messages` returns the ordered thread. A member's own posts never count against their unread state, and `POST /api/channels/{channel_id}/read` records a `ChannelRead` event that advances that member's read position to the current message count.

In the PWA, the **Channels** screen lists the active member's authorized channels with unread badges, opens a thread, and sends messages. Sends go through the same durable outbox as every other command, so a message composed offline is queued with its client-generated ID and synchronizes exactly once on reconnection.

### Milestone 2: Season Design Journey

Build the full 12-week season plan flow, review/refinement dates, Coach review, Captain structure, goal and container tracking, scoreboards, and weekly review rhythm.

**Exit:** A participant submits a season plan from a phone; a Coach approves or requests revisions; all template versions and history are retained.

### Milestone 3: 3F Weekly Calibration Loop

Build the six-section weekly read, diagnostic scales, scoreboard and container updates, prior-strike follow-up, submission/reopen states, participant dashboard, Coach review queue, and Captain review queue.

**Exit:** A full weekly cycle runs without email or a spreadsheet; Coaches have reliable review queues; history is understandable in its original context.

### Milestone 4: PWA, Offline Sync, And Notifications

Build installation, offline app shell, local outbox/inbox, idempotent sync, explicit conflicts, Web Push subscriptions, timezone-aware reminders, muting, optional quiet hours, and in-app notification fallback.

**Exit:** A participant completes and submits a weekly read offline, which synchronizes exactly once after reconnection; notification rules are honored.

### Milestone 5: Essential Communication

Build text-only authorized channels, read state, unread counts, offline message queueing, mute controls, and simple moderation/reporting.

**Exit:** The pilot can hold essential program conversations in-app without violating sponsor or private-channel boundaries.

### Milestone 6: Glossary And Guarded Assistant

Build glossary authoring, publishing, versions, access-aware retrieval, assistant responses with sources, escalation to Coach, and AI audit records.

**Exit:** Members receive attributable framework guidance; unsupported requests are declined or routed to human support.

### Milestone 7: Pilot, Learn, And Adjust

Run one controlled Crucible or pre-Crucible simulation. Review completion, review turnaround, offline sync success, notification conversion, active use, operating overhead, and qualitative feedback weekly. Fix reliability blockers immediately and prioritize only evidence-backed improvements.

## Explicitly Deferred

- Autonomous junior Coach or Success Team agents.
- AI scoring, diagnosis, risk classification, or client-specific recommendations.
- Rich chat features: attachments, reactions, threaded replies, voice/video, and broad social feeds.
- Advanced analytics, benchmarking, payments, CRM, marketing, and native mobile applications.
- Fully generic workflow builders.

## First Vertical Slice

The first implementation should demonstrate one complete, deployable flow:

1. An administrator creates a Crucible and assigns a participant to a Coach.
2. The participant installs the PWA and completes a short Season Design Journey.
3. The participant submits the plan online or offline.
4. The Coach receives it, approves or requests revision, and the participant receives the response.
5. The participant completes one 3F System Read, including a scale assessment and deliberate strikes.
6. Offline changes synchronize exactly once after reconnection.
7. The Coach reviews the read and posts participant-visible feedback.
8. Every state change is represented by a durable domain event and shown through a projection.

This vertical slice establishes the product's core operating loop and the technical patterns required for a real pilot.
