from app.timing import clock, layout


def test_reflow_follows_durations_and_order():
    plan = layout([20, 30, 20, 20], "19:30")
    assert [(b["rel_start"], b["rel_end"]) for b in plan["blocks"]] == [(0, 20), (20, 50), (50, 70), (70, 90)]
    assert [(b["clock_start"], b["clock_end"]) for b in plan["blocks"]][-1] == ("20:40", "21:00")
    assert (plan["total"], plan["end"]) == (90, "21:00")

    # Change a duration mid-plan, then reorder: everything after it shifts.
    plan = layout([20, 45, 20, 20], "19:30")
    assert plan["blocks"][2]["clock_start"] == "20:35" and plan["end"] == "21:15"
    assert layout([20, 20, 45, 20], "19:30")["blocks"][2]["clock_start"] == "20:10"


def test_empty_plan_and_midnight():
    assert layout([], "19:30") == {"blocks": [], "total": 0, "end": "19:30"}
    assert clock("23:50", 20) == "00:10"
