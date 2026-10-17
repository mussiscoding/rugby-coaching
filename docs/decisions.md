# Decisions

These are the non-obvious choices and why we made them. The D-numbers match the v1 plan (`docs/plans/2026-10-16-feat-rugby-session-planner-v1-plan.md`), which has the full detail. Add new entries at the bottom, and only after John has confirmed them.

---

## Secret links, not logins (D4, D5)

There are two secret links, one for coaches (edit) and one for players (read-only). Visiting `/join/<key>` sets a signed cookie holding the role and a fingerprint of the key. Changing a key logs out everyone holding the old link. Coaches pick their name once per device. That's attribution, not authorisation, in the same spirit as susyncki.

We considered the `happy`-style `#k=` fragment, but a server-rendered app never receives the fragment. Real per-person logins are too much for six coaches, and soft delete covers mistakes and vandalism.

## Activities, not drills (D25)

The library items are "activities". A drill is one specific kind of skill zone, so the word can't cover warm-ups and game zones too. Types follow the RFU structure: warm-up / skill zone / game zone.

## A block has 1..N groups (D6)

One group means everyone together, and two or more means a split. There's no separate "kind" column. Splits never cross block boundaries, which matches how sessions actually run: you split, then everyone comes back together.

## Coaching points are rows, starred by link (D7)

Coaching points and "what good looks like" are rows in `activity_points`. A session stars the ones it wants to draw out through `group_focus_points`. Rewording a point updates everywhere; deleting one archives it, so old sessions still show what was stressed.

## Description is free text with suggested headings (D8)

Set up / How to run / Progressions are suggested `## ` headings in one free-text field, not columns. Coaches can delete any of them. `summary` stays its own one-line field, because the picker and the player view need a short line.

## Live reference to activities (brainstorm)

Editing an activity updates it everywhere, including past sessions. Session-specific things (why today, starred points, how it went) live on the group, so they're unaffected.

## Concurrent edits (D17)

- **Session edits are taps that save immediately, and the last save wins.** You see other people's changes on your next tap.
- **Activities are long, considered text, so editing one takes a 2-hour lock with no override.** Once the 2 hours are up, someone else can take the lock. If they do, your save comes back with your text intact rather than overwriting theirs.

We rejected live cursors as a project in themselves.

## Raw sqlite3, sync (D18)

This is the same raw-SQL style as susyncki, without the async plumbing. Connections open inside endpoints (FastAPI runs sync dependencies and their teardown on different threads), and every write runs in `BEGIN IMMEDIATE`.

## Full-page responses with hx-boost (D19)

Every save redirects back to the page. One edit can shift every later block's clock time, so re-rendering the whole page is always right, where swapping fragments isn't. HTMX fragments are only used for the picker's live search.

## Coaches are a table (D24)

Coaches are filled from the `COACHES` setting and never deleted; leavers get `active = 0`. Every "who did this" column points at a coach row.

## Internal slug vs display name (D26)

`rugby-coaching` is the permanent internal name; the brand exists only as `APP_NAME`. This avoids the dance-time/wonderland split, where the brand leaked into service names, config and templates.

## Frugal testing (D23)

This is a local club tool, so tests cover only access control, player-view redaction and timing maths.
