"""test_mocking.py
Demonstrates pytest + mocking (unittest.mock / pytest-mock) to isolate
and simulate scenarios for the multi-agent system -- this lab's third
learning outcome: "Utilize pytest and mocking libraries to simulate
various scenarios and validate agent behavior."

Three mocking techniques are shown here, each solving a different
problem that a plain unit/integration test doesn't:

  1. Fake ("mock") agents -- test MessageBus in isolation, without
     depending on any *real* agent's business logic at all.
  2. Spies (mocker.patch.object(..., wraps=...)) -- verify a real agent
     called `send()` with exactly the right arguments, without needing
     to inspect bus history indirectly.
  3. Fault injection (side_effect) -- simulate a failing agent to
     understand/document how the system behaves under failure, which
     you can't provoke at all with the well-behaved agents in agents.py.
"""
from unittest.mock import Mock
import pytest

from agents import MessageBus, Message, DecisionAgent, RouterAgent


# ---------------------------------------------------------------------------
# 1. Isolating MessageBus with fake agents
# ---------------------------------------------------------------------------

def test_bus_send_targeted_calls_receive_on_recipient_only():
    """Test MessageBus.send() in isolation using a Mock agent -- no real
    agent logic is involved, so this only fails if the *bus's* dispatch
    logic breaks."""
    bus = MessageBus()
    fake_agent = Mock()
    fake_agent.name = "fake"
    bus.register(fake_agent)

    msg = Message(sender="tester", recipient="fake", topic="ping", payload={"n": 1})
    bus.send(msg)

    fake_agent.receive.assert_called_once_with(msg)


def test_bus_send_broadcast_calls_receive_on_every_registered_agent():
    bus = MessageBus()
    agent_a, agent_b = Mock(), Mock()
    agent_a.name, agent_b.name = "a", "b"
    bus.register(agent_a)
    bus.register(agent_b)

    msg = Message(sender="tester", recipient=None, topic="broadcast", payload={})
    bus.send(msg)

    agent_a.receive.assert_called_once_with(msg)
    agent_b.receive.assert_called_once_with(msg)


def test_bus_send_to_unknown_recipient_is_recorded_but_not_delivered():
    bus = MessageBus()
    msg = Message(sender="tester", recipient="ghost", topic="x", payload={})
    bus.send(msg)  # should not raise -- no agent named "ghost" is registered
    assert bus.history() == [msg]


# ---------------------------------------------------------------------------
# 2. Spying on real agents with mocker.patch.object(..., wraps=...)
# ---------------------------------------------------------------------------

def test_router_calls_send_with_expected_forwarding_args(mocker):
    """Patch RouterAgent.send (wrapping the real implementation) so we can
    assert exactly what it forwards, on top of the real routing logic
    actually running."""
    bus = MessageBus()
    router = RouterAgent("router", mapping={"echo.": "echoer", "score": "decider"})
    bus.register(router)
    router.on_start()

    spy = mocker.patch.object(router, "send", wraps=router.send)

    bus.send(Message(sender="client", recipient="router", topic="echo.ping", payload={"x": 1}))

    spy.assert_called_once_with(recipient="echoer", topic="echo.ping", payload={"x": 1})


def test_decision_agent_send_called_with_computed_decision(mocker):
    bus = MessageBus()
    decider = DecisionAgent("decider")
    bus.register(decider)
    decider.on_start()

    spy = mocker.patch.object(decider, "send", wraps=decider.send)

    bus.send(Message(sender="client", recipient="decider", topic="score",
                      payload={"value": 0.9, "threshold": 0.5}))

    spy.assert_called_once_with("client", "decision", {
        "accepted": True, "value": 0.9, "threshold": 0.5
    })


# ---------------------------------------------------------------------------
# 3. Simulating a failure scenario that the real agents can't produce
# ---------------------------------------------------------------------------

def test_bus_propagates_exception_from_a_failing_agent():
    """Documents CURRENT behavior: if one agent's receive() raises during a
    broadcast, MessageBus.send() does not isolate the failure -- it
    propagates immediately, and any agent registered after the failing one
    never gets notified. This is exactly the kind of scenario mocking lets
    you simulate that you can't provoke with the well-behaved agents in
    agents.py, and it's a useful regression test to have in place *before*
    hardening the bus with per-agent error isolation."""
    bus = MessageBus()
    flaky = Mock()
    flaky.name = "flaky"
    flaky.receive.side_effect = RuntimeError("boom")
    healthy = Mock()
    healthy.name = "healthy"

    bus.register(flaky)
    bus.register(healthy)

    with pytest.raises(RuntimeError, match="boom"):
        bus.send(Message(sender="tester", recipient=None, topic="broadcast", payload={}))

    healthy.receive.assert_not_called()


def test_bus_send_is_still_recorded_in_history_even_if_delivery_later_fails():
    """The history append happens before dispatch, so a crashing agent
    doesn't erase the audit trail of what was attempted."""
    bus = MessageBus()
    flaky = Mock()
    flaky.name = "flaky"
    flaky.receive.side_effect = RuntimeError("boom")
    bus.register(flaky)

    msg = Message(sender="tester", recipient="flaky", topic="x", payload={})
    with pytest.raises(RuntimeError):
        bus.send(msg)

    assert bus.history() == [msg]
