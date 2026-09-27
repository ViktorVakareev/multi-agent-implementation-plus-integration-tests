"""agents.py
Starter implementations for a simple multi-agent system used in the lab
'Designing and Validating Test Suites for a Multi-Agent AI System'.

This version includes EchoAgent and DecisionAgent for testing.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --------------------------
# Messaging primitives
# --------------------------

@dataclass
class Message:
    sender: str
    recipient: Optional[str]  # None means broadcast
    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """A minimal in-memory message bus."""
    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        self._history: List[Message] = []

    def register(self, agent: "BaseAgent") -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent name already registered: {agent.name}")
        self._agents[agent.name] = agent
        agent._bus = self

    def send(self, msg: Message) -> None:
        self._history.append(msg)
        if msg.recipient:
            agent = self._agents.get(msg.recipient)
            if agent:
                agent.receive(msg)
        else:
            for agent in self._agents.values():
                agent.receive(msg)

    def history(self) -> List[Message]:
        return list(self._history)


# --------------------------
# Base Agent
# --------------------------

class BaseAgent:
    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Agent name must be a non-empty string")
        self.name = name
        self._bus: Optional[MessageBus] = None
        self._inbox: List[Message] = []

    def on_start(self) -> None:
        """Hook called after registration."""
        pass

    def send(self, recipient: Optional[str], topic: str, payload: Dict[str, Any]) -> None:
        if not self._bus:
            raise RuntimeError("Agent is not registered on a MessageBus")
        msg = Message(sender=self.name, recipient=recipient, topic=topic, payload=payload)
        self._bus.send(msg)

    def receive(self, msg: Message) -> None:
        """Default behavior: enqueue and call handle()."""
        self._inbox.append(msg)
        self.handle(msg)

    def handle(self, msg: Message) -> None:
        """Override with agent-specific logic."""
        pass

    @property
    def inbox(self) -> List[Message]:
        return list(self._inbox)


# --------------------------
# EchoAgent
# --------------------------

class EchoAgent(BaseAgent):
    """Echoes messages back to sender if topic is 'echo' or starts with 'echo.'"""
    def handle(self, msg: Message) -> None:
        if msg.topic == "echo" or msg.topic.startswith("echo."):
            self.send(recipient=msg.sender, topic="echo.reply", payload={"echo": msg.payload})


# --------------------------
# DecisionAgent
# --------------------------

class DecisionAgent(BaseAgent):
    """Makes simple decisions based on numeric score."""
    def handle(self, msg: Message) -> None:
        if msg.topic == "score":
            value = msg.payload.get("value")
            threshold = msg.payload.get("threshold", 0)
            if not isinstance(value, (int, float)):
                self.send(msg.sender, "decision", {"error": "invalid_value"})
                return
            accepted = value >= threshold
            self.send(msg.sender, "decision", {
                "accepted": accepted,
                "value": value,
                "threshold": threshold
            })


# --------------------------
# RouterAgent
# --------------------------

class RouterAgent(BaseAgent):
    """Routes messages based on topic prefixes."""
    def __init__(self, name: str, mapping: Dict[str, str]) -> None:
        super().__init__(name)
        self.mapping = dict(mapping)

    def handle(self, msg: Message) -> None:
        if msg.sender == self.name:
            return
        if msg.topic.endswith(".reply"):
            return

        target = None
        for key, agent_name in self.mapping.items():
            if key.endswith("."):
                if msg.topic.startswith(key):
                    target = agent_name
                    break
            else:
                if msg.topic == key:
                    target = agent_name
                    break
        if target:
            self.send(recipient=target, topic=msg.topic, payload=msg.payload)
