"""test_agents.py
Unit tests for individual agents in agents.py.

Run with:
    pytest -q --cov=agents --cov-report=term-missing

The `bus_and_agents` fixture is defined once in conftest.py and shared
with test_integration.py.
"""
import pytest
from agents import MessageBus, BaseAgent, EchoAgent, DecisionAgent, RouterAgent, Message

# ---------- EchoAgent ----------

def test_echo_agent_replies_with_same_payload(bus_and_agents):
    bus, echoer, decider, router = bus_and_agents
    msg = Message(sender="tester", recipient="echoer", topic="echo", payload={"x": 1})
    bus.send(msg)
    history = bus.history()
    assert any(m.topic == "echo.reply" and m.recipient == "tester" for m in history)

def test_echo_agent_ignores_non_echo_topics(bus_and_agents):
    bus, echoer, *_ = bus_and_agents
    before = len(bus.history())
    bus.send(Message(sender="tester", recipient="echoer", topic="not-echo", payload={}))
    after = len(bus.history())
    assert (after - before) == 1

# ---------- DecisionAgent ----------

@pytest.mark.parametrize("value,threshold,accepted", [
    (0.9, 0.5, True),
    (0.1, 0.5, False),
    (5, 5, True),
])
def test_decision_agent_threshold_logic(bus_and_agents, value, threshold, accepted):
    bus, _, decider, _ = bus_and_agents
    bus.send(Message(sender="tester", recipient="decider", topic="score",
                     payload={"value": value, "threshold": threshold}))
    decision_msgs = [m for m in bus.history() if m.topic == "decision" and m.recipient == "tester"]
    assert decision_msgs, "Expected a decision reply"
    assert decision_msgs[-1].payload["accepted"] is accepted

def test_decision_agent_handles_invalid_value(bus_and_agents):
    bus, _, decider, _ = bus_and_agents
    bus.send(Message(sender="tester", recipient="decider", topic="score",
                     payload={"value": "NaN"}))
    replies = [m for m in bus.history() if m.topic == "decision" and m.recipient == "tester"]
    assert replies[-1].payload.get("error") == "invalid_value"

def test_decision_agent_ignores_non_score_topics(bus_and_agents):
    bus, _, decider, _ = bus_and_agents
    before = len(bus.history())
    bus.send(Message(sender="tester", recipient="decider", topic="chatter", payload={}))
    after = len(bus.history())
    assert (after - before) == 1  # no reply generated

# ---------- RouterAgent ----------
#
# NOTE: sending through router.send(recipient=None, ...) broadcasts to every
# registered agent, including echoer/decider directly -- so it exercises
# EchoAgent/DecisionAgent matching their own topics, but never actually
# drives RouterAgent.handle()'s forwarding branches (router ignores its own
# broadcast message because `msg.sender == self.name`). To genuinely test
# the router's forwarding logic, a message has to be addressed *directly*
# to "router" so router is the only agent that processes it.

def test_router_forwards_by_topic_prefix(bus_and_agents):
    bus, echoer, decider, router = bus_and_agents
    router.send(recipient=None, topic="echo.hello", payload={"txt": "hi"})
    assert any(m.topic == "echo.reply" for m in bus.history())

def test_router_exact_match_for_score(bus_and_agents):
    bus, echoer, decider, router = bus_and_agents
    router.send(recipient=None, topic="score", payload={"value": 1.0, "threshold": 2.0})
    assert any(m.topic == "decision" for m in bus.history())

def test_router_forwards_prefix_match_when_addressed_directly(bus_and_agents):
    """Drives RouterAgent.handle()'s prefix-matching branch directly.

    Note: RouterAgent.send() constructs the forwarded Message with itself
    as `sender` (not the original client), so EchoAgent's reply is
    addressed back to "router", not to "client". This is a real behavior
    of the current implementation (no reply-path/correlation tracking),
    not a testing mistake -- see test_router_does_not_preserve_original_sender
    below for a test that documents this limitation explicitly.
    """
    bus, echoer, decider, router = bus_and_agents
    bus.send(Message(sender="client", recipient="router", topic="echo.ping", payload={"n": 1}))
    assert any(m.sender == "router" and m.recipient == "echoer" and m.topic == "echo.ping"
               for m in bus.history())
    assert any(m.topic == "echo.reply" and m.recipient == "router" for m in bus.history())

def test_router_forwards_exact_match_when_addressed_directly(bus_and_agents):
    """Drives RouterAgent.handle()'s exact-match branch directly."""
    bus, echoer, decider, router = bus_and_agents
    bus.send(Message(sender="client", recipient="router", topic="score",
                      payload={"value": 1.0, "threshold": 0.5}))
    assert any(m.sender == "router" and m.recipient == "decider" and m.topic == "score"
               for m in bus.history())
    # The decision reply goes back to "router" (the forwarded message's
    # sender), not to "client" -- see the note above.
    decisions = [m for m in bus.history() if m.topic == "decision" and m.recipient == "router"]
    assert decisions and decisions[-1].payload["accepted"] is True

def test_router_does_not_preserve_original_sender_on_forward(bus_and_agents):
    """Documents a real limitation: because RouterAgent.send() always uses
    itself as the message sender, a client that only talks to the router
    never receives the specialist agent's reply directly -- it goes back
    to the router instead. A production version would need to carry the
    original sender (e.g. in `meta`) and have specialists reply to that
    instead of to `msg.sender`."""
    bus, echoer, decider, router = bus_and_agents
    bus.send(Message(sender="client", recipient="router", topic="echo.ping", payload={}))
    assert not any(m.recipient == "client" for m in bus.history())

def test_router_drops_unroutable_topic_when_addressed_directly(bus_and_agents):
    """No mapping entry matches -> target stays None -> nothing is forwarded."""
    bus, echoer, decider, router = bus_and_agents
    before = len(bus.history())
    bus.send(Message(sender="client", recipient="router", topic="unknown.topic", payload={}))
    after = len(bus.history())
    assert (after - before) == 1  # only the original message, no forward

def test_router_ignores_its_own_broadcast(bus_and_agents):
    """RouterAgent.handle() returns immediately when it is the sender."""
    bus, echoer, decider, router = bus_and_agents
    router.send(recipient=None, topic="score", payload={"value": 1.0, "threshold": 2.0})
    forwarded_by_router = [m for m in bus.history() if m.sender == "router" and m.topic == "score"]
    # the only "score" message from router is the original broadcast itself
    assert len(forwarded_by_router) == 1

def test_router_ignores_reply_topics(bus_and_agents):
    """RouterAgent.handle() returns immediately for '.reply' topics, so a
    reply is never re-routed into a forwarding loop."""
    bus, echoer, decider, router = bus_and_agents
    before = len(bus.history())
    bus.send(Message(sender="echoer", recipient="router", topic="echo.reply", payload={}))
    after = len(bus.history())
    assert (after - before) == 1  # router did not forward or reply

# ---------- BaseAgent ----------

def test_base_agent_default_handle_is_a_noop_and_enqueues_message(bus_and_agents):
    bus, *_ = bus_and_agents
    base = BaseAgent("base")
    bus.register(base)
    base.on_start()
    bus.send(Message(sender="tester", recipient="base", topic="anything", payload={"a": 1}))
    assert len(base.inbox) == 1
    assert base.inbox[0].topic == "anything"

def test_base_agent_inbox_returns_a_copy_not_the_live_list(bus_and_agents):
    bus, *_ = bus_and_agents
    base = BaseAgent("base")
    bus.register(base)
    base.on_start()
    bus.send(Message(sender="tester", recipient="base", topic="x", payload={}))
    snapshot = base.inbox
    snapshot.append("mutating the returned list should not affect the agent")
    assert len(base.inbox) == 1

# ---------- Edge cases & utilities ----------

def test_agent_requires_nonempty_name():
    with pytest.raises(ValueError):
        EchoAgent("")

def test_agent_requires_nonempty_name_rejects_whitespace_only():
    with pytest.raises(ValueError):
        EchoAgent("   ")

def test_message_bus_register_duplicate_name():
    bus = MessageBus()
    a1 = EchoAgent("dup")
    a2 = EchoAgent("dup")
    bus.register(a1)
    with pytest.raises(ValueError):
        bus.register(a2)

def test_agent_send_without_registering_on_a_bus_raises():
    orphan = EchoAgent("orphan")
    with pytest.raises(RuntimeError):
        orphan.send(recipient=None, topic="echo", payload={})
