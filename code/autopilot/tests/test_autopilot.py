from autopilot.policy import Autopilot


def test_decide_returns_plan():
    a = Autopilot()
    plan = a.decide({}, {"has_code": True})
    assert plan["trim"] is True
    assert "use_cache" in plan
