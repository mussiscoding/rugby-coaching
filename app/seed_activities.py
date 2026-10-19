"""Starter activities, inserted only into an empty library on first boot (D20).

After that the coaches own the library: edits happen in the app, not here.
Written in our own words (not copied from RFU material). John reviews the
rugby before launch.
"""

from app.db import db, now_iso, tx

# Each entry: (key, fields, coaching points, what good looks like). `key` is only
# used below to wire up related links.
ACTIVITIES = [
    # --- From John (dictated 2026-10-18). Lines marked [guess] are Claude's fill-ins to check. ---
    ("overlaps", dict(
        name="Overlaps", type="skill", default_duration_min=15,  # [guess] minutes
        players="6–24", coaches_needed=1, space="Channels 10m wide × 20m",  # [guess] players, space
        summary="2v1 up to 4v3 in channels: fix the first defender and support with depth.",
        tags="attack,handling,decision-making",
        description="""## Set up
Channels about 10m wide. Attackers start on the try line, defenders 10m in front.

## How to run
Coach feeds the ball to the attack. Attack plays the overlap on the call; defenders touch or tackle depending on the session.

## Progressions
- 2v1
- 3v2
- 4v3

## Variations
- Passing decisions: one pass to the attacker with no defender on them
- Create the 2v1: fix the first defender and always pass to the 2nd man, who then has a 2v1
""",
    ), ["Fix the first defender", "Depth of support"],
       ["The first defender is committed before the pass", "Support runners arrive deep and at pace"]),  # [guess] what good looks like

    ("guards-bodyguards", dict(
        name="Guards and bodyguards touch", type="game", default_duration_min=15,  # [guess] minutes
        players="16+", coaches_needed=1, space="30 × 30m or bigger",
        summary="Even-numbers touch where defenders must always set a guard and bodyguard.",
        tags="attack,defence,game,communication",
        description="""## Set up
Two even teams, 30 × 30m or bigger.

## How to run
Normal touch. On a touch the ball carrier goes fully to ground, as if tackled, and presents the ball. The defending team must put in a guard and a bodyguard either side of the ruck, on one knee. Missing them means a fitness punishment.
""",
    ), ["Draw defenders in", "Get on one edge to create space", "Identify the spaces"],
       ["Players running at spaces", "10 looking up for gaps before receiving the ball", "Defenders talking about guards"]),

    ("bounce-5-20", dict(
        name="5-bounce 20-bounce", type="fitness", default_duration_min=5,
        players="Any", coaches_needed=1, space="20m × (players) m",
        summary="Shuttle runs with a drop to the stomach at every line.",
        tags="fitness,conditioning",
        description="""## Set up
Everyone on a line, lying on their stomachs.

## How to run
- Run out to 5m, down on stomachs
- Back to the start line, down on stomachs
- Run out to 20m, down on stomachs
- Back to the 15m line, down on stomachs
- Out to the 20m line, down on stomachs
- Run back to the start line
Repeat as many times as the session needs.

## Progressions
- 1, 2, 3 or more repeats before a rest
""",
    ), ["Chest all the way to the floor every time", "Drive up and out of the ground"],  # [guess] coaching points
       ["Everyone touching every line", "Pace held on the last rep"]),  # [guess] what good looks like

    ("lineout-in-front", dict(
        name="Lineouts: getting in front", type="skill", default_duration_min=30,
        players="4+ (two lifters, a jumper, a thrower)", coaches_needed=1, space="Touchline, 15m",  # [guess] space
        summary="Pods of three practise catching over the front lifter's head, not over the jumper's own.",
        tags="set piece,lineout,forwards",
        description="""## Set up
Pods of three (two lifters and a jumper) plus a thrower.

## How to run
The goal is for the jumper to catch the ball over the head of the front lifter, not over their own head.
""",
    ), ["Jumper leans forwards, not straight up", "Front lifter's hands go straight up, not the usual pyramid shape"],
       ["Ball taken in front, above the front lifter's head"]),  # [guess] what good looks like

    ("come-ruck-123", dict(
        name="1, 2, 3 come ruck with me", type="game", default_duration_min=15,  # [guess] minutes
        players="12–30", coaches_needed=1, space="Half pitch",  # [guess] players, space
        summary="Attack looks after the ball while the coach's call decides how hard defenders can contest.",
        tags="breakdown,rucking,contact,game",
        description="""## Set up
Two equal teams. Half the defenders have shields.

## How to run
The attacking team's goal is to look after the ball and score. The coach calls what the defenders can do:
- 1: defenders just make tackles
- 2: defenders can counter-ruck
- 3: defenders can jackal
""",
    ), ["Look after the ball first", "Support arrives before the defender can contest"],  # [guess] coaching points
       ["Quick, clean ball on every call", "Attack still scores at level 3"]),  # [guess] what good looks like

    ("ruck-body-position", dict(
        name="Ruck body position", type="skill", default_duration_min=20,
        players="3+", coaches_needed=1, space="Small area per three",
        summary="Threes work on a low, powerful body position, then compete for a rolled ball.",
        tags="breakdown,rucking,contact",
        description="""## Set up
Groups of three.

## How to run
- One-on-one body position work (scrum-style), with the third player assessing the form of the other two
- Rucking drill: all three lie on their backs, facing the same way, about an arm's length apart. The middle player has the ball and rolls to one side. Whoever they roll to is the attack, looking after the ruck; the other tries to get the ball off them.
""",  # [guess] "one-on-one Scrum position work" and "rocking drill" were read as body-position work and a rucking drill
    ), ["Tower of power", "Hips below shoulders", "Feet in the right position",
        "Too far forward and we can't get low enough", "Too far back and we have no power"],
       ["Flat backs, hips below shoulders", "The ball stays on the attack's side"]),  # [guess] what good looks like

    ("activate", dict(
        name="Activate warm-up", type="warmup", default_duration_min=15,  # [guess] minutes
        players="Any", coaches_needed=1, space="10m × 1m per player",
        summary="England Rugby's Activate injury-prevention warm-up: movement, balance and speed build-up.",
        tags="warm-up,injury prevention,speed",
        description="""## How to run
- S-shaped runs
- Slow knees to chest
- Hops
- Leg swings
- Lunge with a twist
- Lunge with a lean
- Fast feet → 70% sprint
- Fast feet → 90% sprint
""",
        # Coaching points are from England Rugby's "Key Activate" cues.
    ), ["Knee over toes", "Hip, knee, ankle in line", "Chest up, head neutral", "Brace through the trunk", "Soft knees on landing"],
       ["Quality movement every rep, not rushing", "Knees tracking over toes on lunges and hops"]),  # [guess] what good looks like

    # Placeholders John wants in the library; to be filled in.
    ("backline-depth", dict(name="Backline depth", type="skill"), [], []),
    ("backline-shape", dict(name="Backline set shape (alignment)", type="skill"), [], []),
    ("blitz-defence", dict(name="Blitz defence", type="skill"), [], []),
    ("lineout-mauls", dict(name="Lineout mauls", type="skill"), [], []),
    ("scrum-shape", dict(name="Scrum shape", type="skill"), [], []),
    ("team-run", dict(name="Team run-through", type="game"), [], []),

    # --- Claude's original starters: still to review (keep / change / drop). ---
    # --- Warm-ups -------------------------------------------------------------
    ("touch", dict(
        name="Touch warm-up", type="warmup", default_duration_min=15,
        players="10–30", coaches_needed=1, space="Half pitch",
        summary="Easy-paced touch to get bodies moving and hands on the ball.",
        tags="warm-up,handling,communication",
        description="""## Set up
Two even teams, bibs, one ball. Touch = tackle; six touches then turnover.

## How to run
Start at walking pace for two minutes, then build to a jog, then game speed for the last few minutes. Coach stops it only for safety or a quick reset.

## Progressions
- Ball carrier must pass within two seconds of a touch
- Only offloads allowed after a touch
- Add a second ball
""",
    ), ["Run onto the ball, don't wait for it", "Talk early: call for it", "Width — use the whole pitch"],
       ["Constant talking", "Ball moving wide, not just one-out runners"]),

    ("movement", dict(
        name="Movement prep", type="warmup", default_duration_min=10,
        players="Any", coaches_needed=1, space="20m lanes",
        summary="Dynamic stretches and running drills to prepare for contact and sprinting.",
        tags="warm-up,injury prevention,speed",
        description="""## Set up
Players in lines of 4–5 behind cones, 20m lanes.

## How to run
Each drill out and back: jog, high knees, heel flicks, walking lunges with twist, leg swings, side shuffles, carioca, then three build-up sprints at 60%, 80% and 100%.
""",
    ), ["Quality over speed until the sprints", "Stay tall on the running drills", "Full range of movement"],
       ["Everyone warm and slightly out of breath", "No one skipping the last sprint"]),

    ("handling-lines", dict(
        name="Handling lines", type="warmup", default_duration_min=10,
        players="8–30", coaches_needed=1, space="20 × 20m",
        summary="Lines passing on the move to wake up hands before skills work.",
        tags="warm-up,handling,passing",
        description="""## Set up
Groups of four in a line, one ball each group, jogging up a 20m channel.

## How to run
Pass along the line while jogging; the end player carries the ball back. Swap direction each length so both hands work.

## Progressions
- Increase speed
- Pass must be caught with hands out in front
- Call a name: that player has to come round for a loop
""",
    ), ["Hands up, show a target", "Pass across the body, follow through to the target", "Run straight"],
       ["Ball arrives at chest height, out in front", "Line stays flat and evenly spaced"]),

    ("contact-prep", dict(
        name="Contact prep", type="warmup", default_duration_min=10,
        players="Pairs", coaches_needed=1, space="Grid 15 × 15m",
        summary="Gradual build-up to contact so bodies are ready before tackling or rucking.",
        tags="warm-up,contact,tackle",
        description="""## Set up
Pairs of similar size in a grid. Tackle shields if available.

## How to run
Build intensity in stages: shoulder taps, hand wrestles for position, walking hits on shields, then jogging hits on shields. Swap roles every round.

## Progressions
- Add a ball carrier who has to protect the ball through light contact
""",
    ), ["Cheek to cheek — head to the side", "Feet keep driving after contact", "Build up gradually, never jump straight to full speed"],
       ["Safe head position every time", "Players ready to move into full contact work"]),

    # --- Skill zones -------------------------------------------------------------
    ("ruck-clear", dict(
        name="Ruck clear-out 2v1", type="skill", default_duration_min=15,
        players="6–18", coaches_needed=1, space="10 × 10m grids",
        summary="Two attackers secure the ball at the breakdown against one jackaling defender.",
        tags="breakdown,rucking,contact",
        description="""## Set up
Grids 10 × 10m. A ball carrier, one support player, one defender with a shield or none.

## How to run
Ball carrier goes to ground and presents the ball. Support player arrives and clears the defender beyond the ball. Rotate roles every rep.

## Progressions
- Add a second defender arriving late
- Support starts further back
- Scrum half picks up and passes to finish the rep
""",
    ), ["Low body height on entry", "Drive beyond the ball, not into the pile", "Arrive quickly: the first two seconds win it"],
       ["Ball available in under 3 seconds", "Cleaners stay on their feet"]),

    ("tackle", dict(
        name="Tackle technique", type="skill", default_duration_min=15,
        players="Pairs", coaches_needed=1, space="5m channels",
        summary="Safe, effective tackling from kneeling up to walking pace.",
        tags="defence,tackle,contact",
        description="""## Set up
Pairs in 5m channels, tackle tubes or shields if available.

## How to run
Work through stages: kneeling, crouching, walking. Only move on when the technique is right.

## Progressions
- Kneeling
- Crouching start
- Walking ball carrier
- Jogging ball carrier, chosen side
""",
    ), ["Eyes on the ball carrier's hips", "Cheek to cheek: head behind, never in front", "Arms wrap and squeeze", "Leg drive to finish"],
       ["Head safely on the side of the ball carrier every time", "Tackler finishes on top"]),

    ("passing-move", dict(
        name="Passing on the move", type="skill", default_duration_min=15,
        players="8–24", coaches_needed=1, space="30 × 20m",
        summary="Pass and catch at pace while running straight.",
        tags="handling,passing,attack",
        description="""## Set up
Lines of four, 30m wide channel, a ball per group.

## How to run
Run the length passing along the line; the receiver takes it at pace. Swap ends each run.

## Progressions
- Spin pass for longer gaps
- Short pop pass on a cut line
- Add one passive defender
""",
    ), ["Catch early, hands out", "Hips straight while you pass", "Receiver accelerates onto the ball"],
       ["Ball doesn't drift backwards along the line", "Runners keep their speed through the catch"]),

    ("lineout", dict(
        name="Lineout throw and lift", type="skill", default_duration_min=20,
        players="Forwards, 6–9 per group", coaches_needed=1, space="Touchline, 15m",
        summary="Forwards practise calls, throwing and lifting for clean ball from the lineout.",
        tags="set piece,lineout,forwards",
        description="""## Set up
Hooker on the touchline, jumper and two lifters per pod. Mark the 5m and 15m lines.

## How to run
Walk-through of the calls first, then live throws to the front, middle and back. Count clean takes out of ten.

## Progressions
- Add a passive opposition jumper
- Ball to the scrum half off the top
- Move into a maul after the catch
""",
    ), ["Call early and clearly", "Lifters set before the jump: hands ready", "Thrower and jumper agree on the timing"],
       ["Ball caught at the top of the jump", "Clean ball to the scrum half"]),

    ("kicking", dict(
        name="Kicking skills", type="skill", default_duration_min=20,
        players="Backs, any number", coaches_needed=1, space="Half pitch",
        summary="Backs practise box kicks, grubbers and kick chase.",
        tags="kicking,backs",
        description="""## Set up
Kickers in pairs facing each other 20–30m apart, plus chasers.

## How to run
Rotate through kick types: punts for distance, box kicks off the base, grubbers through a gap. Chasers try to compete for every catch.

## Progressions
- Kick under pressure from a defender
- Kick and chase as a group of three
""",
    ), ["Drop the ball onto the foot, don't throw it", "Follow through towards the target", "Chasers stay onside and in a line"],
       ["Kicks are contestable, not just long", "Chasers arrive as the ball lands"]),

    ("line-speed", dict(
        name="Defensive line speed", type="skill", default_duration_min=15,
        players="8–20", coaches_needed=1, space="30 × 20m",
        summary="Defenders practise getting off the line together to cut down attacking time.",
        tags="defence,communication",
        description="""## Set up
Defensive line of 4–6 facing an attacking line 10m away. Cones mark the gain line.

## How to run
Attack passes along the line on the coach's call; defence moves up together and must touch the right player.

## Progressions
- Attack can run a switch or loop
- Increase attack numbers so defence has to drift
""",
    ), ["Up together, stay connected", "Talk: inside and outside calls", "Line speed, then control before contact"],
       ["No gaps or dog-legs in the line", "Attack is behind the gain line when touched"]),

    ("presentation", dict(
        name="Carry and present", type="skill", default_duration_min=10,
        players="Pairs or threes", coaches_needed=1, space="10 × 10m",
        summary="Ball carriers practise going into contact and presenting the ball for support.",
        tags="breakdown,contact,carrying",
        description="""## Set up
Ball carrier and a shield holder; a third player as support.

## How to run
Carrier hits the shield, goes to ground and places the ball back at arm's length. Support player secures it.

## Progressions
- Shield holder tries to wrap up the ball
- Carrier has to step before contact
""",
    ), ["Ball in two hands into contact", "Land on your side, back to the opposition", "Long place, back towards your team"],
       ["Ball clearly presented for the scrum half", "Carrier lands safely every time"]),

    # --- Game zones ----------------------------------------------------------------
    ("numbers-up", dict(
        name="Numbers-up attack game", type="game", default_duration_min=15,
        players="12–24", coaches_needed=1, space="30 × 22m",
        summary="Attack with more players than defence to practise creating and finishing overlaps.",
        tags="attack,decision-making,game",
        description="""## Set up
Attack of 6–7 against defence of 4–5 in a wide channel.

## How to run
Coach feeds the ball, attack plays until a try or turnover. Rotate defenders out regularly.

## Progressions
- Defence gets an extra player after each try
- Defence starts closer
""",
    ), ["Fix defenders before passing", "Width first, then attack the space"],
       ["The extra player is used to score", "Attack scores in under four phases"]),

    ("ruck-game", dict(
        name="Touch-to-ruck game", type="game", default_duration_min=15,
        players="12–30", coaches_needed=1, space="Half pitch",
        summary="Game where a touch means the carrier goes to ground and support must clear the ruck.",
        tags="breakdown,rucking,game",
        description="""## Set up
Two teams, shields for defenders if you want to limit contact.

## How to run
On a touch the ball carrier goes to ground and presents; the first two attackers clear one defender. Score if the ball comes out within three seconds.

## Progressions
- Two defenders can contest
- Full contact at the ruck only
""",
    ), ["Support arrives in pairs", "Low body height on entry"],
       ["Quick ball every ruck", "Defenders driven beyond the ball"]),

    ("defence-game", dict(
        name="Line speed defence game", type="game", default_duration_min=15,
        players="12–24", coaches_needed=1, space="30 × 22m",
        summary="Even-numbers game where the defence scores by stopping the attack behind the gain line.",
        tags="defence,tackle,game",
        description="""## Set up
Even teams, gain line marked with cones.

## How to run
Normal game (touch or contact). Defence scores a point for every touch made behind the gain line.

## Progressions
- Attack gets an extra player
- Full contact
""",
    ), ["Up together", "Talk every phase"],
       ["Most tackles made behind the gain line", "No gaps in the line"]),

    ("kick-tennis", dict(
        name="Kick tennis", type="game", default_duration_min=15,
        players="8–16", coaches_needed=1, space="Two 20m zones with a 10m gap",
        summary="Two teams kick back and forth; points for kicks the other side can't catch.",
        tags="kicking,backs,game",
        description="""## Set up
Two zones 20m deep with a 10m no-man's land between them.

## How to run
Teams kick from their zone into the other team's zone. A point if the ball lands uncaught in the zone.

## Progressions
- Only box kicks allowed
- Kickers must be under pressure from one chaser
""",
    ), ["Kick to space, not to people", "Call the catch"],
       ["Contestable, accurate kicks", "Catchers call early and take it cleanly"]),

    ("set-piece-phase", dict(
        name="Lineout to first phase", type="game", default_duration_min=20,
        players="Full squad", coaches_needed=2, space="Half pitch",
        summary="Forwards win the lineout and backs run a first-phase move against light defence.",
        tags="set piece,lineout,attack,game",
        description="""## Set up
Forwards in lineout formation, backs lined up, a few defenders.

## How to run
Call the lineout and move. Run it walk-through first, then at full speed with defence.

## Progressions
- Opposition jumper contests
- Defence goes from touch to full contact
""",
    ), ["Calls are clear for forwards and backs", "Backs stay onside and run hard lines"],
       ["Clean lineout ball to the backs", "Move ends over the gain line"]),
]

RELATED = [
    # From John
    ("overlaps", "guards-bodyguards"), ("ruck-body-position", "come-ruck-123"),
    ("lineout-in-front", "lineout"), ("lineout-in-front", "set-piece-phase"),  # "all other lineout and throwing" ones
    ("lineout-in-front", "lineout-mauls"), ("lineout", "lineout-mauls"),
    # Claude's starters (to review)
    ("overlaps", "numbers-up"), ("ruck-clear", "ruck-game"), ("presentation", "ruck-game"),
    ("tackle", "defence-game"), ("line-speed", "defence-game"), ("passing-move", "guards-bodyguards"),
    ("kicking", "kick-tennis"), ("lineout", "set-piece-phase"), ("contact-prep", "tackle"),
]


def seed_if_empty() -> None:
    with db() as conn:
        if conn.execute("SELECT 1 FROM activities LIMIT 1").fetchone():
            return
        now = now_iso()
        ids: dict[str, int] = {}
        with tx(conn):
            for key, fields, coaching, looks_like in ACTIVITIES:
                cols = list(fields) + ["created_at", "updated_at"]
                cur = conn.execute(
                    f"INSERT INTO activities ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    list(fields.values()) + [now, now],
                )
                ids[key] = cur.lastrowid
                for kind, texts in (("coaching", coaching), ("looks_like", looks_like)):
                    for position, text in enumerate(texts):
                        conn.execute(
                            "INSERT INTO activity_points (activity_id, kind, text, position) VALUES (?, ?, ?, ?)",
                            (cur.lastrowid, kind, text, position),
                        )
            for a, b in RELATED:
                x, y = sorted((ids[a], ids[b]))
                conn.execute("INSERT INTO activity_links (activity_a, activity_b) VALUES (?, ?)", (x, y))
