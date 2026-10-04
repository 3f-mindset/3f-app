# 3F App Execution Backlog

This file is the source of truth for the autonomous delivery loop. Work one item at a time, in priority order. Mark an item complete only after implementation, required verification, documentation updates where applicable, and a Conventional Commit.

## Current Milestone: Coach Review And Operational Visibility

- [x] **P0 - Enforce assigned-Coach calibration review.** Require the reviewer to be the participant's assigned Coach, prevent unassigned review submission, and add authorization tests.
- [x] **P0 - Build Coach review workflow.** In the Coach Anvil, open an assigned student's submitted calibration, show the six 3F sections in context, and submit participant-visible feedback or a revision request.
- [x] **P0 - Show participant feedback.** Render Coach feedback and revision state in the participant Anvil, including a clear next action after a requested revision.
- [x] **P1 - Build Captain visibility.** Allow Captains to see assigned Coach completion/review status through relationship-checked records; do not expose participant private calibration content by default.
- [x] **P1 - Add an administrator setup view.** Provide a development-only UI for creating a Crucible, enrolling members, creating assignments, and setting up circles/channels through the existing APIs.

## Next Milestone: Reliable Weekly Operation

- [x] **P1 - Version templates.** Persist versioned Season Plan and 3F calibration templates with the exact prompts and scale definitions used for a submission.
- [x] **P1 - Add calibration reopen events.** Let an assigned Coach request a revision, reopen the correct weekly record, and preserve submission history.
- [x] **P1 - Add weekly due-state projection.** Project opened, due soon, overdue, submitted, and reviewed state for each participant and week.
- [x] **P2 - Complete offline command recovery.** Add an explicit outbox status view, retry action, and conflict state for rejected queued commands.

## Later Milestones

- [x] **P2 - Add authorized text channels.** Persist messages, unread state, offline sends, and channel relationship authorization.
- [x] **P2 - Add notification preferences.** Implement device subscriptions, channel mutes, opt-in quiet hours, and timezone-aware reminder policy.
- [ ] **P3 - Add approved knowledge glossary.** Support draft, publish, archive, version, browse, and search states.
- [ ] **P3 - Add guarded client assistant.** Retrieve only approved knowledge, cite sources, and escalate to the assigned Coach.

## Definition Of Done

Every completed item must satisfy all applicable checks:

1. Domain and authorization behavior is covered by automated tests.
2. `cd backend && uv run pytest` passes.
3. `cd web && npm run build` passes for frontend changes.
4. `git diff --check` passes.
5. The Compose stack is still healthy when the change affects a running service.
6. Documentation is updated if the interface, command, or operating workflow changed.
7. The work is committed using Conventional Commits.
