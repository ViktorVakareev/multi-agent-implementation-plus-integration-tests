"""main.py
Minimal runnable example showing how agents interact on the MessageBus.
Learners can run this file to observe message passing and extend as needed.
"""
from agents import MessageBus, EchoAgent, DecisionAgent, RouterAgent

def build_system():
    bus = MessageBus()
    echoer = EchoAgent("echoer")
    decider = DecisionAgent("decider")
    router = RouterAgent("router", mapping={
        "echo.": "echoer",
        "score": "decider",
    })
    for a in (echoer, decider, router):
        bus.register(a)
        a.on_start()
    return bus, echoer, decider, router

if __name__ == "__main__":
    bus, echoer, decider, router = build_system()
    # Simulate a client message: send to router (broadcast) so it can route by topic
    # In a real system a client would be another agent; here we reuse router as entry point
    router.send(recipient=None, topic="echo", payload={"text": "hello"})
    router.send(recipient=None, topic="score", payload={"value": 0.72, "threshold": 0.5})

    # Print bus history for a quick glance
    for i, m in enumerate(bus.history(), 1):
        print(f"{i:02d} {m.sender} -> {m.recipient or '*'} [{m.topic}] {m.payload}")