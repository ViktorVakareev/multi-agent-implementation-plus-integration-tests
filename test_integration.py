"""test_integration.py
Integration test template for end-to-end multi-agent interactions.

Focus:
  * message routing through RouterAgent
  * collaboration between EchoAgent and DecisionAgent
  * ensuring bus history records expected flows
  * mocked-dependency interactions (Step 3/6 of the lab): patching one
    agent's own processing method with a canned response/failure and
    exercising the *real* caller (RouterAgent) around it

The `bus_and_agents` fixture is defined once in conftest.py and shared
with test_agents.py.
"""
import pytest

from agents import Message, DecisionAgent

def test_end_to_end_workflow_echo_and_decision(bus_and_agents):
    bus, echoer, decider, router = bus_and_agents

    # Step 1: client sends an echo via router (broadcast)
    router.send(recipient=None, topic="echo.request", payload={"text": "ping"})
    # Step 2: client sends a scoring request
    router.send(recipient=None, topic="score", payload={"value": 0.75, "threshold": 0.5})

    history = bus.history()

    # Verify at least one echo reply was produced
    assert any(m.topic == "echo.reply" for m in history)
    # Verify a decision message exists and is accepted
    decisions = [m for m in history if m.topic == "decision"]
    assert decisions, "Expected a decision message"
    assert decisions[-1].payload.get("accepted") is True

def test_unroutable_message_is_dropped(bus_and_agents):
    bus, echoer, decider, router = bus_and_agents
    before = len(bus.history())
    router.send(recipient=None, topic="unknown.topic", payload={})
    after = len(bus.history())
    # Only the original send should be recorded; no new forwards
    assert (after - before) == 1

def test_client_addresses_router_directly_and_gets_routed_end_to_end(bus_and_agents):
    """A more realistic integration flow: an external client only knows
    about the router and sends it a *targeted* message (not a broadcast).
    The router does forward to the right specialist agent -- but the
    specialist's reply is addressed back to "router" (the forwarded
    message's sender), not to "client". This integration test captures
    that real end-to-end limitation rather than assuming a reply path
    that the current RouterAgent doesn't actually implement."""
    bus, echoer, decider, router = bus_and_agents

    bus.send(Message(sender="client", recipient="router", topic="echo.hi", payload={"text": "hi"}))
    bus.send(Message(sender="client", recipient="router", topic="score",
                      payload={"value": 0.8, "threshold": 0.3}))

    history = bus.history()

    # The specialists did process the forwarded messages...
    replies_to_router = [m for m in history if m.recipient == "router"]
    topics_to_router = {m.topic for m in replies_to_router}
    assert "echo.reply" in topics_to_router
    assert "decision" in topics_to_router

    # ...but none of that ever reaches "client" directly.
    assert not any(m.recipient == "client" for m in history if m.sender != "client")

def test_multiple_agents_can_be_addressed_in_sequence_without_cross_talk(bus_and_agents):
    """Sanity check that routing one topic doesn't leak a reply to the
    agent that handles a different topic."""
    bus, echoer, decider, router = bus_and_agents

    bus.send(Message(sender="client", recipient="router", topic="score",
                      payload={"value": 0.1, "threshold": 0.9}))

    # Only the decider should ever have been the forwarding target; echoer
    # should not appear anywhere as a sender/recipient in this exchange.
    assert not any(m.sender == "echoer" or m.recipient == "echoer" for m in bus.history())

# ---------------------------------------------------------------------------
# Mocked-dependency integration tests (lab Step 3 / Step 6 pattern):
# replace one agent's own processing logic wholesale with a canned
# return_value/side_effect, then exercise the *real* RouterAgent around it
# and assert on the resulting interaction. This isolates "does the router
# forward correctly?" from "is DecisionAgent's own scoring logic correct?" --
# the latter is already covered separately in test_agents.py.
# ---------------------------------------------------------------------------

def test_router_to_decider_integration_with_mocked_decision_logic(bus_and_agents, mocker):
    """Mocked-success case: DecisionAgent's real handle() is replaced with a
    canned reply. The router's forwarding is exercised for real; only the
    specialist's own logic is faked."""
    bus, echoer, decider, router = bus_and_agents

    def fake_handle(self, msg):
        self.send(msg.sender, "decision", {"mocked": True, "accepted": True})

    mocker.patch.object(DecisionAgent, "handle", fake_handle)

    bus.send(Message(sender="client", recipient="router", topic="score",
                      payload={"value": 1, "threshold": 0}))

    decisions = [m for m in bus.history() if m.topic == "decision"]
    assert decisions, "Expected the router to have forwarded to the (mocked) decider"
    assert decisions[-1].payload == {"mocked": True, "accepted": True}

def test_router_to_decider_integration_when_decision_logic_fails(bus_and_agents, mocker):
    """Mocked-failure case (mirrors the lab's `side_effect=Exception(...)`
    pattern): DecisionAgent's handle() is replaced with something that
    raises. Unlike a hand-rolled Agent/AgentA/AgentB example that might
    catch this and return a clean "Error: ..." string, this codebase has
    no per-agent fault isolation -- the exception propagates straight out
    of MessageBus.send(), and the client never receives any reply at all.
    This test documents that real, current integration behavior."""
    bus, echoer, decider, router = bus_and_agents

    mocker.patch.object(DecisionAgent, "handle", side_effect=RuntimeError("decision engine down"))

    with pytest.raises(RuntimeError, match="decision engine down"):
        bus.send(Message(sender="client", recipient="router", topic="score",
                          payload={"value": 1, "threshold": 0}))

    # The client is left hanging -- no decision, no error reply, nothing.
    assert not any(m.recipient == "client" for m in bus.history())
