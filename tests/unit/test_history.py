from verienvelope.errors import VeriEnvelopeError
from verienvelope.history import append_history, assert_history_extends, make_event


def test_append_keeps_the_previous_event_byte_for_byte() -> None:
    first = make_event(
        event_type="confirmed",
        previous_state=None,
        new_state="confirmed",
        reason="initial observation",
        evidence_refs=["ev-1"],
        timestamp="2026-09-26T00:00:00Z",
    )
    result = {"history": [first]}
    second = make_event(
        event_type="evaluation_defect",
        previous_state="confirmed",
        new_state="evaluation_defect",
        reason="the earlier confirmation was wrong",
        evidence_refs=["ev-2"],
        timestamp="2026-09-26T01:00:00Z",
    )
    updated = append_history(result, second)
    assert updated["history"][0] == first
    assert updated["history"][1]["event_type"] == "evaluation_defect"
    assert result["history"] == [first]


def test_truncated_history_is_rejected() -> None:
    first = make_event(
        event_type="component_failure",
        previous_state=None,
        new_state="component_failure",
        reason="stdout differed",
        evidence_refs=["ev-1"],
        timestamp="2026-09-26T00:00:00Z",
    )
    try:
        assert_history_extends([first], [])
    except VeriEnvelopeError as exc:
        assert "truncated" in str(exc) or "prefix" in str(exc)
    else:
        raise AssertionError("truncated history was accepted")


def test_rewritten_prefix_is_rejected() -> None:
    first = make_event(
        event_type="confirmed",
        previous_state=None,
        new_state="confirmed",
        reason="initial",
        evidence_refs=[],
        timestamp="2026-09-26T00:00:00Z",
    )
    rewritten = dict(first)
    rewritten["reason"] = "silently edited"
    try:
        assert_history_extends([first], [rewritten])
    except VeriEnvelopeError:
        return
    raise AssertionError("edited history prefix was accepted")
