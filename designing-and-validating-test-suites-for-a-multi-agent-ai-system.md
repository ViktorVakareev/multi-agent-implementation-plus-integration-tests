Designing and Validating Test Suites for a Multi-Agent AI System
📋 Overview
Time Estimate: 25 minutes

In this ungraded lab activity, you will design and validate comprehensive test suites for a simplified multi-agent AI system. This lab is crucial for understanding how to ensure that individual agents within the system communicate effectively and handle data correctly. By implementing unit tests for individual agents and integration tests for agent interactions, you will gain practical experience in verifying agent communication logic and data handling. This activity culminates in a continuous integration (CI) simulation, where you will confirm that your test suite maintains a coverage target of 88%. This skill is vital in real-world applications where robust testing ensures the reliability of AI systems.

 🎯 Learning Outcomes  
By the end of this lab, you will be able to:

Design and implement unit tests for individual agents in a multi-agent AI system.

Develop integration tests to verify interactions between agents and ensure correct communication logic.

Utilize pytest and mocking libraries to simulate various scenarios and validate agent behavior.
----------
Step 1

Starting Point
Ready to get started? Select Launch Jupyter Notebook to access your Lab.

🚀 Starting Point

Access the starter code files:

Open the project folder in VS Code using the following path:  

/home/coder/coursera/vscode/projects

Then, navigate to the PROJECTS directory and view the following starter files located inside it:

agents.py

main.py

test_agents.py

test_integration.py

These files contain the starter code you will use throughout this lab.

🔧 GitHub setup: Not applicable for this lab.

🛠️ Required tools/setup: Ensure you have pytest,pytest-mock and pytest-cov installed. You can do this by running the following command in the VS Code terminal:

1
pip install pytest pytest-mock pytest-cov
----
Step 2

Lab instructions
1 of 7 completed


inLabInstructionsPart~bJWzfsByEfClggr_50fVoQ
​
In this activity, you will focus on verifying that each agent behaves as expected when given valid and invalid inputs.

Steps:

1. Open the agents.py file and review the individual agents. Each agent should have its own methods for processing data.

2. In the test_agents.py file, create unit tests for each agent.

Example:

12345
def test_agent_process_valid_input(mocker):
    mock_data = "Valid input data"
    agent = Agent()
    result = agent.process(mock_data)
    assert result == "Expected output"
3. Execute the tests using the command:

12
python3 -m pytest -v test_agents.py

💡 Tip: Focus on edge cases while writing your unit tests to ensure comprehensive coverage.

🤖 GitHub Copilot Exploration: Type this comment and see what Copilot suggests: # Suggest unit tests for Agent class methods.

⚙️ Test Your Work

Run the command:

1
python3 -m pytest -v test_agents.py
Expected output: All tests should pass without errors.
----
Step 3

inLabInstructionsPart~6nAshsByEfClggr_50fVoQ
​
In this activity, you will verify that agents communicate correctly and handle data as expected.

Steps:

1. Review how agents communicate with each other in the main.py file. Identify key interaction points that need to be tested.

2. In the test_integration.py file, write tests that simulate the interactions between agents.

Example:

123456
def test_agent_interaction(mocker):
    mock_response = "Mocked response from Agent B"
    mocker.patch('AgentB.process', return_value=mock_response)
    agent_a = AgentA()
    result = agent_a.communicate_with_agent_b("Input data")
    assert result == "Expected interaction output"
 3. Execute the tests using the command:

1
python3 -m pytest -v test_integration.py
💡 Tip: Ensure that your mocks accurately represent the expected behavior of the agents during interactions.

🤖 GitHub Copilot Exploration: Type this comment and see what Copilot suggests: 

1
# Suggest integration tests for Agent communication methods.
⚙️ Test Your Work

Run the command:

1
python3 -m pytest -v test_integration.py
Expected output: All tests should pass without errors.
-----
Step 4

inLabInstructionsPart~BR_hBcB0EfClggr_50fVoQ
​
In this final activity, you will ensure that your test suite meets the required coverage target.

Steps:

1. Use the pytest-cov plugin to check your test coverage. Run the following command:

1
python3 -m pytest -v --cov=agents --cov-report=html
2. This will generate an HTML coverage report that you can open in your browser.

3. Ensure that your overall coverage is at least 88%. If it is lower, review your tests and identify areas where you can add more coverage.

4. Create a CI configuration file (e.g., .github/workflows/ci.yml) that runs your tests and checks for coverage. Here’s a sample configuration:

12345678910111213141516171819
name: CI for Multi-Agent System

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python

💡 Tip: Regularly run your tests and coverage checks to maintain code quality as your project evolves.

🤖 GitHub Copilot Exploration: Type this comment and see what Copilot suggests:

1
# Suggest CI configuration for pytest coverage.
⚙️ Test Your Work

Run the command:

1
python3 -m pytest -v --cov=agents --cov-report=html
Expected output: Coverage report generated with at least 88% coverage.
----

Step 5

inLabInstructionsPart~uE4-WsB0EfCf0g5ZHvFLkw
​
 ✅ Success Checklist
Unit tests for individual agents are implemented and pass without errors.

Integration tests for agent interactions are implemented and pass without errors.

Test coverage report indicates at least 88% coverage.

CI configuration file is created and correctly set up.

🔍 Common Issues & Solutions
Problem: Tests fail due to incorrect agent logic.

Solution: Review the agent methods and ensure they handle inputs correctly.

Problem: Coverage is below 88%.

Solution: Review your tests and add additional cases to cover untested paths.

➡️ Summary
🔑 Key Points
Designing comprehensive test suites is essential for ensuring the reliability of multi-agent AI systems.

Unit and integration tests help verify both individual agent functionality and agent interactions.

Continuous integration practices support maintaining code quality and coverage over time.
----
Step 6

# Complete working solution with task markers in comments

# Unit tests for Agent class
def test_agent_process_valid_input(mocker):
    mock_data = "Valid input data"
    agent = Agent()
    result = agent.process(mock_data)
    assert result == "Expected output"

def test_agent_process_invalid_input(mocker):
    mock_data = "Invalid input data"
    agent = Agent()
    result = agent.process(mock_data)
    assert result == "Error: Invalid input"

# Integration tests for agent interactions
def test_agent_interaction(mocker):
    mock_response = "Mocked response from Agent B"
    mocker.patch('AgentB.process', return_value=mock_response)
    agent_a = AgentA()
    result = agent_a.communicate_with_agent_b("Input data")
    assert result == "Expected interaction output"

def test_agent_interaction_failure(mocker):
    mocker.patch('AgentB.process', side_effect=Exception("Agent B failure"))
    agent_a = AgentA()
    result = agent_a.communicate_with_agent_b("Input data")
    assert result == "Error: Agent B failure"

This code includes unit tests for valid and invalid inputs for an agent, as well as integration tests for interactions between agents. You can replace the "Expected output" and other strings with the actual expected outcomes based on your implementation.  
---

