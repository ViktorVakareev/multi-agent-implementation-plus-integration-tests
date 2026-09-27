"""conftest.py
Shared pytest fixtures for the multi-agent test suite.

Both the unit tests (test_agents.py) and the integration tests
(test_integration.py) need the same wired-up system: a MessageBus with
an EchoAgent, a DecisionAgent, and a RouterAgent registered on it. That
setup lived as two near-duplicate fixtures before; centralizing it here
keeps the suite DRY and is the standard pytest pattern for sharing
fixtures across test modules in the same directory.
"""
import pytest

from agents import MessageBus, EchoAgent, DecisionAgent, RouterAgent


@pytest.fixture()
def bus_and_agents():
    """A fully wired bus + (echoer, decider, router), ready to exercise."""
    bus = MessageBus()
    echoer = EchoAgent("echoer")
    decider = DecisionAgent("decider")
    router = RouterAgent("router", mapping={"echo.": "echoer", "score": "decider"})
    for a in (echoer, decider, router):
        bus.register(a)
        a.on_start()
    return bus, echoer, decider, router
