# Multi-Agent Test Suite

A small in-memory multi-agent system, built to practice designing and
validating test suites for AI agent systems: unit tests, integration
tests, mocking, and a coverage-gated CI pipeline.

<!--
  Coverage/test badges: generate these yourself after running the suite
  (see "Generating badges & screenshots" below), then point these at the
  files you create, e.g.:
  ![Coverage](docs/badges/coverage.svg) ![Tests](docs/badges/tests.svg)
  ![CI](https://github.com/<your-username>/<your-repo>/actions/workflows/ci.yml/badge.svg)
-->

- **34 tests, 100% statement coverage** on `agents.py` (required gate: 88%)
- Pure standard library + `pytest` / `pytest-cov` / `pytest-mock` — no external services, no network calls, runs in milliseconds

---

## Table of contents

- [What this project is](#what-this-project-is)
- [How the system works](#how-the-system-works)
  - [Message](#message)
  - [MessageBus](#messagebus)
  - [BaseAgent](#baseagent)
  - [EchoAgent](#echoagent)
  - [DecisionAgent](#decisionagent)
  - [RouterAgent](#routeragent)
  - [Message flow examples](#message-flow-examples)
  - [Known limitation: RouterAgent doesn't preserve the original sender](#known-limitation-routeragent-doesnt-preserve-the-original-sender)
- [Project layout](#project-layout)
- [The test suite, file by file](#the-test-suite-file-by-file)
  - [conftest.py — shared fixture](#conftestpy--shared-fixture)
  - [test_agents.py — unit tests](#test_agentspy--unit-tests)
  - [test_integration.py — integration tests](#test_integrationpy--integration-tests)
  - [test_mocking.py — mocking-focused tests](#test_mockingpy--mocking-focused-tests)
- [Coverage and the CI gate](#coverage-and-the-ci-gate)
- [Setup](#setup)
- [Running things](#running-things)
- [VS Code integration](#vs-code-integration)
- [Generating badges & screenshots](#generating-badges--screenshots)
- [Publishing to GitHub](#publishing-to-github)
- [Success checklist](#success-checklist)

---

## What this project is

`agents.py` implements a minimal **multi-agent system**: independent
`Agent` objects that don't call each other directly, but instead
communicate only by passing `Message` objects through a shared
`MessageBus` — the same publish/subscribe pattern real multi-agent AI
systems use so agents stay decoupled from one another's internals.

The rest of the project is a **test suite** built around that system,
organized to demonstrate three distinct testing techniques:

1. **Unit tests** — does each agent's own logic behave correctly in
   isolation, including on invalid input?
2. **Integration tests** — do agents correctly communicate and hand
   off work to each other through the bus, end to end?
3. **Mocking** — can we isolate the bus from real agent logic (fake
   agents), spy on a real agent's calls without changing its behavior,
   and simulate failures that the well-behaved real agents can't
   otherwise produce?

...plus a coverage-gated CI configuration so any future change that
drops test coverage below 88% fails the build automatically.

## How the system works

### Message

```python
@dataclass
class Message:
    sender: str
    recipient: Optional[str]   # None means broadcast to every agent
    topic: str                  # what the message is about, e.g. "score"
    payload: Dict[str, Any]     # the actual data being sent
    meta: Dict[str, Any]        # free-form metadata (unused by any agent today)
```

A `Message` is a plain, immutable-in-spirit data record. `recipient=None`
means "broadcast" — every registered agent will see it.

### MessageBus

The `MessageBus` is the only thing agents are allowed to talk to
directly. It has three responsibilities:

- **`register(agent)`** — adds an agent under its (unique) name, and
  gives the agent a reference back to the bus so it can send messages
  later. Raises `ValueError` on a duplicate name.
- **`send(msg)`** — records the message in history, then delivers it:
  - if `msg.recipient` is set, only that named agent's `receive()` is
    called (silently a no-op if no agent by that name is registered);
  - if `msg.recipient` is `None`, **every** registered agent's
    `receive()` is called, including the sender itself.
- **`history()`** — returns every message ever sent, in order — the
  audit trail the test suite uses to assert on what actually happened.

Note what `send()` does **not** do: it doesn't catch exceptions from an
agent's `receive()`. If one agent's handling code raises, that
exception propagates straight out of `send()` and no further agents in
that broadcast get notified. See
["Known limitation"](#known-limitation-routeragent-doesnt-preserve-the-original-sender)
and `test_mocking.py`'s fault-injection tests for what this means in
practice.

### BaseAgent

Every concrete agent inherits from `BaseAgent`, which provides:

- `__init__(name)` — validates the name is non-empty (raises `ValueError` otherwise).
- `send(recipient, topic, payload)` — builds a `Message` (with `sender=self.name`) and hands it to the bus. Raises `RuntimeError` if the agent was never `register()`-ed on a bus.
- `receive(msg)` — the bus calls this on delivery. The default implementation appends the message to the agent's private inbox, then calls `self.handle(msg)`.
- `handle(msg)` — **this is what subclasses override.** The base implementation is a no-op.
- `inbox` (property) — returns a *copy* of every message this agent has received, so callers can't mutate the agent's internal state by mutating the returned list.
- `on_start()` — an optional hook called once, right after registration (none of the current agents use it, but it's there for subclasses that need to do setup once they know they're wired up).

### EchoAgent

The simplest possible agent. If a message's topic is exactly `"echo"`
or starts with `"echo."`, it replies to the sender with topic
`"echo.reply"` and the original payload wrapped as `{"echo": <payload>}`.
Anything else, it silently ignores.

### DecisionAgent

Implements a threshold decision: on topic `"score"`, it reads
`payload["value"]` and `payload["threshold"]` (default `0`) and replies
with `"decision"`:

- if `value` isn't a number, replies `{"error": "invalid_value"}`
- otherwise replies `{"accepted": value >= threshold, "value": ..., "threshold": ...}`

Any other topic is silently ignored.

### RouterAgent

Built with a `mapping: Dict[str, str]` from topic pattern → target
agent name (e.g. `{"echo.": "echoer", "score": "decider"}`). A pattern
ending in `.` is treated as a **prefix match**; anything else must
match the topic **exactly**.

On `handle(msg)`:
1. If `msg.sender == self.name` (i.e. this is the router's own earlier
   broadcast coming back around), or the topic ends in `.reply`, it
   returns immediately — it never re-routes its own traffic or a reply.
2. Otherwise it walks `mapping` in order, looking for the first
   prefix or exact match, and if found, forwards the message (same
   topic and payload) to that target agent.
3. If nothing matches, the message is silently dropped.

### Message flow examples

**Broadcast through the router** (what `main.py` and several older
tests do):

```
router.send(recipient=None, topic="echo", payload={"text": "hello"})
```

This broadcasts to *every* agent at once. `EchoAgent` matches the
`"echo"` topic itself and replies directly — `RouterAgent`'s own
forwarding logic is never actually exercised here, because the router
sees its own broadcast come back (`msg.sender == self.name`) and
returns immediately. This is a subtle but important distinction the
test suite makes explicit (see `test_router_ignores_its_own_broadcast`).

**Targeted message directly to the router** (what actually exercises
`RouterAgent`'s forwarding logic):

```
bus.send(Message(sender="client", recipient="router", topic="echo.ping", payload={}))
```

Only `router` receives this. It matches `"echo."` in its mapping and
forwards a **new** message to `"echoer"` — but with `sender="router"`,
not `"client"` (see the limitation below). `echoer` then replies to
`"router"`, not to `"client"`.

### Known limitation: RouterAgent doesn't preserve the original sender

`RouterAgent.send()` (inherited from `BaseAgent`) always constructs the
forwarded message with `sender=self.name`. That means when a specialist
agent replies, it replies to `"router"` — the original external client
never gets a direct reply. This was discovered by writing tests that
address the router directly instead of only broadcasting through it
(see `test_router_does_not_preserve_original_sender_on_forward` and
`test_client_addresses_router_directly_and_gets_routed_end_to_end`).

It's not a crash — the system still "works" — but it means `RouterAgent`
can't currently act as a transparent proxy for a client expecting a
reply. A fix would carry the original sender through (e.g. in
`Message.meta`) and have specialist agents reply to that instead of to
`msg.sender`.

There's a second, related limitation the mocking tests document:
**no per-agent fault isolation**. If one agent's `receive()`/`handle()`
raises during a broadcast, `MessageBus.send()` does not catch it — the
exception propagates immediately, and any agent later in registration
order is never notified at all (see `test_mocking.py` and
`test_router_to_decider_integration_when_decision_logic_fails`).

## Project layout

```
agents.py             # Message, MessageBus, BaseAgent, EchoAgent, DecisionAgent, RouterAgent
main.py               # runnable demo of agents talking over the bus
conftest.py           # shared pytest fixture (bus_and_agents)
test_agents.py         # unit tests: individual agent behavior + edge cases
test_integration.py    # integration tests: end-to-end + mocked-dependency workflows
test_mocking.py        # mocking/spying/fault-injection tests (pytest-mock, unittest.mock)
pytest.ini             # pytest config: coverage on by default, --cov-fail-under=88
requirements.txt       # pytest, pytest-cov, pytest-mock
ci_simulate.py         # local "CI" run: pytest + coverage gate, CI-style pass/fail summary
.gitignore             # excludes venv/, __pycache__/, .pytest_cache/, .coverage, htmlcov/
.github/workflows/ci.yml   # the same coverage gate as a real GitHub Actions workflow
.vscode/settings.json      # enables pytest in VS Code's Test Explorer
.vscode/launch.json        # debug configs for main.py and the current test file
designing-and-validating-test-suites-for-a-multi-agent-ai-system.md  # original lab instructions
```

## The test suite, file by file

### conftest.py — shared fixture

Defines `bus_and_agents`, used by every test file: a fresh `MessageBus`
with an `EchoAgent("echoer")`, `DecisionAgent("decider")`, and
`RouterAgent("router", ...)` all registered and started. Centralizing
this avoids three copies of the same setup code drifting out of sync.

### test_agents.py — unit tests

| Test | What it checks |
|---|---|
| `test_echo_agent_replies_with_same_payload` | `"echo"` topic gets an `"echo.reply"` back |
| `test_echo_agent_ignores_non_echo_topics` | anything else produces no reply |
| `test_decision_agent_threshold_logic` (parametrized) | accept/reject logic across several value/threshold pairs |
| `test_decision_agent_handles_invalid_value` | a non-numeric value replies with `{"error": "invalid_value"}` |
| `test_decision_agent_ignores_non_score_topics` | anything else produces no reply |
| `test_router_forwards_by_topic_prefix` / `test_router_exact_match_for_score` | original broadcast-style routing tests |
| `test_router_forwards_prefix_match_when_addressed_directly` | drives the router's actual forwarding logic (prefix branch) via a **targeted**, non-broadcast message |
| `test_router_forwards_exact_match_when_addressed_directly` | same, for the exact-match branch |
| `test_router_does_not_preserve_original_sender_on_forward` | documents the sender limitation above |
| `test_router_drops_unroutable_topic_when_addressed_directly` | no mapping match → message silently dropped |
| `test_router_ignores_its_own_broadcast` | router doesn't re-route its own broadcast traffic |
| `test_router_ignores_reply_topics` | router never re-routes a `.reply` message |
| `test_base_agent_default_handle_is_a_noop_and_enqueues_message` | the base `handle()` does nothing, but `receive()` still records the message |
| `test_base_agent_inbox_returns_a_copy_not_the_live_list` | mutating `.inbox`'s return value doesn't affect the agent |
| `test_agent_requires_nonempty_name` / `..._rejects_whitespace_only` | name validation |
| `test_message_bus_register_duplicate_name` | registering two agents with the same name raises |
| `test_agent_send_without_registering_on_a_bus_raises` | calling `.send()` before registration raises `RuntimeError` |

### test_integration.py — integration tests

| Test | What it checks |
|---|---|
| `test_end_to_end_workflow_echo_and_decision` | broadcasting an echo and a score request both produce the expected replies |
| `test_unroutable_message_is_dropped` | an unroutable broadcast topic doesn't generate any forwards |
| `test_client_addresses_router_directly_and_gets_routed_end_to_end` | a targeted client→router message really does get forwarded to the right specialist — but the reply lands on `"router"`, not `"client"` (the sender limitation, at integration scope) |
| `test_multiple_agents_can_be_addressed_in_sequence_without_cross_talk` | routing a `"score"` message never involves `echoer` at all |
| `test_router_to_decider_integration_with_mocked_decision_logic` | **mocked-success case**: `DecisionAgent.handle` is replaced with a canned reply; the *real* `RouterAgent` forwarding is exercised around it |
| `test_router_to_decider_integration_when_decision_logic_fails` | **mocked-failure case**: `DecisionAgent.handle` is replaced with something that raises; documents that the exception propagates all the way out of `bus.send()` and the client is left with no reply at all |

### test_mocking.py — mocking-focused tests

Three distinct mocking techniques, each solving a different problem:

1. **Fake agents** (`unittest.mock.Mock`) — test `MessageBus.send()` in
   total isolation from any real agent's logic:
   `test_bus_send_targeted_calls_receive_on_recipient_only`,
   `test_bus_send_broadcast_calls_receive_on_every_registered_agent`,
   `test_bus_send_to_unknown_recipient_is_recorded_but_not_delivered`.
2. **Spies** (`mocker.patch.object(..., wraps=...)`) — let the real
   agent logic run, but assert exactly what arguments it called `send()`
   with: `test_router_calls_send_with_expected_forwarding_args`,
   `test_decision_agent_send_called_with_computed_decision`.
3. **Fault injection** (`side_effect=...`) — simulate a failure the
   real, well-behaved agents can't produce on their own:
   `test_bus_propagates_exception_from_a_failing_agent`,
   `test_bus_send_is_still_recorded_in_history_even_if_delivery_later_fails`.

## Coverage and the CI gate

`pytest.ini` sets:

```ini
[pytest]
addopts = -v --cov=agents --cov-report=term-missing --cov-fail-under=88
testpaths = .
```

So a plain `pytest` run always measures coverage of `agents.py` and
**fails the run** if coverage drops below 88% — this is the same gate
`.github/workflows/ci.yml` enforces on every push/PR, and `ci_simulate.py`
enforces locally with a CI-style pass/fail summary.

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Running things

```bash
# Run the demo (prints the message history to the console)
python main.py

# Run the full test suite (coverage + 88% gate run automatically via pytest.ini)
pytest

# Run just one file
pytest test_mocking.py -v

# Generate an HTML coverage report you can open in a browser
pytest --cov=agents --cov-report=html
# then open htmlcov/index.html

# Run the CI simulation (same gate, with a clear pass/fail summary)
python ci_simulate.py
```

## VS Code integration

Opening this folder in VS Code auto-discovers all tests in the Test
Explorer (the flask/beaker icon in the sidebar) via
`.vscode/settings.json` — no extra configuration needed, as long as the
Python extension is installed and the interpreter is set to the
`.venv` created above (Command Palette → "Python: Select Interpreter").
`.vscode/launch.json` adds two debug configs: one to run `main.py`,
one to debug whichever test file is currently open.

## Generating badges & screenshots

To turn a test run into something visual you can drop into this README
or a GitHub repo. **Create the output folders first** — `coverage-badge`
and `genbadge` don't create missing directories themselves, and writing
to a folder that doesn't exist yet is the most common reason nothing
shows up:

```bash
python -c "import os; os.makedirs('docs/badges', exist_ok=True); os.makedirs('reports', exist_ok=True)"
```

Install both tools (quote the `genbadge[tests]` extra so shells that
treat `[...]` specially don't mangle it), plus `setuptools` --
`coverage-badge` imports `pkg_resources`, which comes from `setuptools`,
and Python 3.12+ virtual environments no longer include it by default,
so without this line you'll hit `ModuleNotFoundError: No module named
'pkg_resources'`:

```bash
pip install coverage-badge "genbadge[tests]" setuptools
```

Run the suite once with a JUnit XML report on top of its normal coverage
run (`pytest.ini` already adds `--cov=agents`, so there's no need to
separately wrap it in `coverage run`):

```bash
pytest --junitxml=reports/junit.xml
```

Now generate both badges from that run's output:

```bash
coverage-badge -o docs/badges/coverage.svg -f
genbadge tests -i reports/junit.xml -o docs/badges/tests.svg
```

If a badge command still produces nothing, run it without redirecting
the error away and read what it prints — `coverage-badge` fails loudly
if no `.coverage` data file exists yet (make sure `pytest` ran
successfully first, in the same folder), and `genbadge` fails loudly if
`reports/junit.xml` doesn't exist (check the `pytest --junitxml=...`
step actually completed).

Then reference them at the top of this README:

```markdown
![Coverage](docs/badges/coverage.svg) ![Tests](docs/badges/tests.svg)
```

**Terminal / HTML report screenshots** (for a portfolio or the course
submission): run `pytest -v` or open `htmlcov/index.html`, then use
Windows' Snipping Tool (`Win + Shift + S`) to capture it, and save into
e.g. `docs/screenshots/test-run.png` / `docs/screenshots/coverage-report.png`.
Embed with `![Test run](docs/screenshots/test-run.png)`.

Note: don't confuse `htmlcov/index.html` (the actual visual coverage
report -- color-coded bars, a sortable per-file table, highlighted
source) with `reports/junit.xml` (a plain machine-readable XML file that
`genbadge` reads to build the tests badge). Opening the `.xml` file
directly in a browser just shows a raw collapsible tree, not a real
report -- that's expected, it isn't meant to be viewed.

**Optional: a nicer-looking test-run report (not just coverage)** --
`pytest-html` turns the whole test run itself into one self-contained,
styled HTML dashboard (pass/fail counts, environment info, expandable
per-test details):

```bash
pip install pytest-html
pytest --html=reports/report.html --self-contained-html
```

Open `reports/report.html` in a browser for something much more visual
to screenshot than the JUnit XML.

**GitHub Actions status badge** (works automatically once pushed —
see the next section):

```markdown
![CI](https://github.com/<your-username>/<your-repo>/actions/workflows/ci.yml/badge.svg)
```

## Publishing to GitHub

```bash
cd path\to\Designing-and-validating-test-suites-for-a-multi-agent-ai-system

git init
git add .
git commit -m "Multi-agent system with unit, integration, and mocking test suite"

# Create the repo on GitHub (pick one):
#   Option A: with the GitHub CLI
gh repo create <your-repo-name> --public --source=. --remote=origin

#   Option B: without the CLI -- create an empty repo at github.com/new,
#   then:
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

git branch -M main
git push -u origin main
```

Once pushed, the workflow in `.github/workflows/ci.yml` runs
automatically on every push/PR (check the "Actions" tab on GitHub) and
enforces the same 88% coverage gate.

## Success checklist

- [x] Unit tests for individual agents are implemented and pass without errors (`test_agents.py`)
- [x] Integration tests for agent interactions are implemented and pass without errors (`test_integration.py`), including mocked-dependency success/failure scenarios
- [x] Test coverage report indicates at least 88% coverage (currently 100% — verified with `pytest --cov=agents --cov-report=html`)
- [x] CI configuration file is created and correctly set up (`.github/workflows/ci.yml`)
