---
date: 2026-10-16
topic: session-planner
---

# Rugby Session Planner

## What We're Building

A small web app for the Finsbury Park Men's coaches (~6 people) to build, share and reuse training session plans. It replaces the weekly WhatsApp message, which can't be edited in place, can't link anywhere, and splits drill details across separate messages. WhatsApp stays the place you share the link.

A **session** has a date, a start time and a **goal** pinned at the top. Below it is a sequence of **blocks** you add with a + button. The button opens a searchable **drill library**: you open a card, read the details, tap "Add to plan" and set a duration (pre-filled from the card's default). A block is either *everyone together* doing one activity, or a **split**: one duration with any number of free-text-labelled groups side by side ("Forwards / Backs", "Front row / Loose forwards / 9&10 / Centres / Back 3", "Main group / New players", "Station 1–4"). Each group gets one activity and a coach. Everyone rejoins when the split ends. Stations are just a split, one group per station.

Coaches add and edit the drills, games and warm-ups themselves. Past sessions form a dated history, and any session can be **copied** as the starting point for this week.

**The app is for pre-planning, not reading during a session.** Coaches read a card before the session. During it, they only glance at it for about 10 seconds ("we've smashed the 4v3s, what's next?") and go back to coaching.

## Core Concepts

**Session**: date, start time, goal, ordered blocks. Shows both relative times (0–20) and clock times (19:30–19:50); changing a duration reflows everything after it.

**Block**: duration plus either one activity or a split into N groups. Each block or group carries:
- **Coach(es) running it** (from the coach list; several allowed)
- **Why today**: how it serves this session's goal (session-specific)
- **Starred coaching points**: pick 1–2 of the drill's points to stress today, or add a session-only one
- **How it went**: an optional post-session note, which rolls up onto the drill card

**Activity card** (the library; renamed from "drill" during planning, since a drill is one kind of skill zone):
- Name, **type**: Warm-up / Skill zone / Game zone (the RFU coaching structure), skill tags
- How to run it (plain text), video link
- Players needed, coaches needed, default duration
- Space required
- **Coaching points**: cues the coach *says* ("low hips, chin up")
- **What good looks like**: what the coach *watches for* ("ball available < 3s")
- **Progressions**: a suggested heading in the activity's free-text description (e.g. one "Overlap" card covering 2v1 → 3v2 → 4v3). The coach decides how far to go based on how the players are doing on the night. Progressions are *not* separate cards or separate blocks.
- **Related drills**: two-way links between cards. The main use is pairing a **skill zone with the game zone** that tests it in a game scenario.
- **Usage**: "Run 7× · last 3 Oct", plus coach-only notes rolled up from past sessions' "how it went" (rows with no note are hidden)

**Session page extras (v1)**:
- Real clock times with reflow
- Warning when a coach is assigned to two places at once

## Access

- **Coach link**: a secret link (`/join/<key>`), which sets a long-lived cookie. Full edit. No passwords. (The `happy` `#k=` fragment doesn't work for a server-rendered app; see plan D4.)
- **Player link**: a separate read-only key. Players only see sessions a coach has marked **Share with players**, and never coach names. Players see **times and a short summary/goal per block**, not the coaching detail. In particular, they never see progressions (so "we only did 2 of 4" isn't visible), coach-only notes or "how it went".
- **"Who are you?" picker for coaches only**, stored per device. Used for "coach running this" and edit attribution. Per `susyncki`: *attribution, not authorisation*. The player link doesn't ask.
- **Coaches are hard-coded** for now (a config list, like `susyncki`'s author slugs).
- **Soft delete everywhere.** This is what makes the wiki-style "anyone can edit" model safe.

## Why This Approach

**Stack: FastAPI + SQLite + Jinja2 + HTMX, no build step.** This matches `dance-time`, `holdings` and `susyncki`. A static JS app with a JSON API (closer to `happy`) was considered and rejected: it puts most of the logic in JavaScript and duplicates the reflow logic across client and server.

Patterns carried over from sibling projects:
- Hosting: `/srv/<slug>`, systemd unit on port 8005, Caddy block, nightly `backup.sh`.
- `requirements.txt` as the single deps file; schema migrations check and fix on startup (no Alembic).
- Docs layout from `dance-time`: `CLAUDE.md`, `docs/working-with-me.md`, `decisions.md`, `brainstorms/`, `plans/`, `jots/`.
- Plain text for drill descriptions. No rich-text editor, because Tiptap forced a build step on `susyncki`.
- Plan local vs prod config and the DB schema properly from day one (lesson from `holdings`).

## Key Decisions

- **Drill types follow the RFU structure**: Warm-up / Skill zone / Game zone.
- **Splits are confined to one block**: they never split and rejoin mid-block, and each group does one activity.
- **Stations are a plain split, not a rotation engine.** (A block-level "rotate every X min" note was dropped for v1; it's an easy column to add later.)
- **Goal linking is a per-block "why today"**, not tags or suggestions.
- **Coaching points ≠ what good looks like**: one is what you say, the other is what you watch for. Both live on the drill; the session stars which to emphasise.
- **Progressions live inside the card** as text; cards link only via "related drills".
- **Live reference to drills**: editing a card updates it everywhere, including past sessions. Session-specific data (why today, stars, how it went) lives on the block, so it's unaffected.
- **One team for now**, without hard-coding it. A squad field can be added later for the women's team.
- **Drill notes come from sessions**, not a separate notes field.
- **Seed the library** with a starter set of drills across all three types, so the picker isn't empty on day one. Write our own descriptions rather than copying RFU text verbatim.
- **Name undecided.** Working slug is `rugby-coaching`; the display name is one config value. Renaming later = new subdomain + Caddy redirect of `/join/*` from the old one; coaches re-tap the link once to get a cookie on the new domain.

## Open Questions

- Exact player-view contents: starred coaching points? "What good looks like"? Or only the "why today" summary?
- App name and subdomain.

## Later / Expansions

- **Equipment** (deliberately out of v1): an equipment section on drill cards, ideally a fixed vocabulary with quantities, enabling a totalled kit list for the session ("6 balls, 20 cones, 4 tackle bags").
- Squads (women's team).
- Coach list managed in-app rather than hard-coded.

## Next Steps

→ `/workflows:plan` for implementation details
