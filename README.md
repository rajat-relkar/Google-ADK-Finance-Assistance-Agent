# Finance Assistance Agent

A small multi-agent personal-finance assistant built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini. A friendly root agent answers general finance questions and looks up the user's financial snapshot. It delegates anything that needs live market data, or savings and investment planning, to a specialist agent that can use Google Search.

> **Status:** learning/prototype project. The user's financial data is mocked (hard-coded).

---

## Features

- **Conversational finance help.** Answers general finance questions and helps plan savings goals in a friendly tone.
- **Personal finance snapshot.** A custom Python tool returns salary, expense breakdown, savings and unallocated income.
- **Exact calculators.** Four deterministic tools (savings rate, required monthly saving, months to goal, future value) so the model never does financial arithmetic itself.
- **Live information via Google Search.** Stock prices, market data, financial news and company information are fetched by a dedicated sub-agent.
- **Agent-as-a-tool pattern.** The search-enabled agent is wrapped in `AgentTool`, so it can sit next to a custom function tool (see [Design notes](#design-notes)).
- **Built-in dev UI.** Run and debug with `adk web` (chat UI, event/trace inspector) or `adk run` (terminal).

## Architecture

```
                 ┌──────────────────────────────────┐
   user ───────▶ │  finance_assistance_agent (root) │
                 │  LlmAgent · gemini-3.5-flash-lite│
                 └───────────────┬──────────────────┘
                                 │ tools
       ┌─────────────────────────┼─────────────────────────────┐
       ▼                         ▼                             ▼
 get_user_personal_      calculate_savings_rate()     AgentTool(investment_plan_agent)
 finance_details()       calculate_required_          LlmAgent · gemini-3.5-flash-lite
 custom tool             monthly_saving()                        │
 (mock data)             calculate_months_to_goal()              ▼
                         calculate_future_value()        google_search (built-in)
                         custom tools (pure Python)
```

| Component | File | Role |
|---|---|---|
| `finance_assistance_agent` (`root_agent`) | [finance_assistance_agent/agent.py](finance_assistance_agent/agent.py) | Entry point. Talks to the user, reads the finance snapshot, runs the calculators, delegates research and investment options. |
| `get_user_personal_finance_details` | [finance_assistance_agent/agent.py](finance_assistance_agent/agent.py) | Function tool returning the user's salary, expenses, savings and unallocated income (mock data). |
| `calculate_*` tools | [finance_assistance_agent/calculators.py](finance_assistance_agent/calculators.py) | Deterministic calculators: savings rate, required monthly saving, months to goal, future value. |
| `investment_plan_agent` | [investment_plan_agent/agent.py](investment_plan_agent/agent.py) | Specialist agent with the built-in `google_search` tool. Handles live data and drafts investment options. |

### Calculators

| Tool | Answers |
|---|---|
| `calculate_savings_rate(monthly_income, monthly_savings)` | What percentage of income is being saved? |
| `calculate_required_monthly_saving(target_amount, months, current_savings=0, annual_return_percent=0)` | How much per month is needed to hit a goal by a deadline? |
| `calculate_months_to_goal(target_amount, monthly_saving, current_savings=0, annual_return_percent=0)` | How long until a goal is reached at a given monthly saving? |
| `calculate_future_value(monthly_contribution, years, annual_return_percent=0, initial_amount=0)` | What will a regular monthly saving or investment grow to? |

Growth-based tools assume monthly compounding at `annual_return_percent / 12` with contributions made at the end of each month. Every tool returns `{"status": "success", ...}` or `{"status": "error", "error_message": ...}`. Because ADK doesn't allow `google_search` and custom tools in one agent, the calculators are attached to the root agent, not to the search agent.

## Project structure

```
ADK_Finance_Assistance_AGent/
├── finance_assistance_agent/      # Root agent package (what `adk web` launches)
│   ├── __init__.py
│   ├── agent.py                   # root_agent + get_user_personal_finance_details tool
│   └── calculators.py             # savings / goal / growth calculator tools
├── investment_plan_agent/         # Sub-agent package (wrapped as a tool by the root agent)
│   ├── __init__.py
│   └── agent.py                   # investment_plan_agent + google_search
├── notes/
│   └── image.png                  # ADK concept diagram (agents, tools, workflow agents)
├── requirements.txt               # google-adk, python-dotenv
├── .gitignore                     # keeps .env, .venv, __pycache__ and .adk/ out of git
└── .env                           # GOOGLE_API_KEY (git-ignored, see Configuration)
```

`finance_assistance_agent/.adk/session.db` is created automatically by ADK to store local chat sessions.

## Prerequisites

- Python **3.11+** (required by `google-adk`)
- A **Gemini API key**: create one in [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your-gemini-api-key
```

ADK walks up from the agent folder until it finds a `.env`, so a single file in the project root works for both agents.

> **Never commit `.env`.** The included [.gitignore](.gitignore) already excludes `.env`, `.venv/`, `__pycache__/` and `.adk/`.

## Running the agent

Run all commands **from the project root** (the folder that contains both agent packages). The root agent imports `investment_plan_agent` as a top-level package, which only resolves when the root is on the Python path.

**Web UI (recommended)**

```powershell
adk web
```

Open the URL it prints (default http://localhost:8000) and pick **finance_assistance_agent** from the agent dropdown.

**Terminal**

```powershell
adk run finance_assistance_agent
```

## Example prompts

| Prompt | What happens |
|---|---|
| "What's my current financial situation?" | Root agent calls `get_user_personal_finance_details`, then `calculate_savings_rate`, and summarises. |
| "What is the latest Tesla stock price?" | Root agent delegates to `investment_plan_agent`, which uses Google Search. |
| "How can I cut my monthly expenses?" | Root agent reads the snapshot and suggests where to trim. |
| "I want to save 5 lakh in 2 years. Can you plan it?" | Root agent asks for any missing inputs (such as risk tolerance), uses `calculate_required_monthly_saving` to size the gap against current savings, then delegates investment options to the planning sub-agent. |
| "If I invest 10,000 a month at 12% for 10 years, what do I end up with?" | Root agent calls `calculate_future_value`. No search needed. |

## Mock data

`get_user_personal_finance_details()` currently returns (monthly amounts, INR):

```python
{
    "currency": "INR",
    "salary": 90000,
    "expense": {"EMI_Expense": 40000, "Entertainment": 5000, "Shopping and Travel": 5000},
    "total_expense": 50000,
    "savings": 10000,
    "unallocated_income": 30000,   # salary - total_expense - savings
}
```

`unallocated_income` makes the 30,000 that is neither spent nor saved explicit, so the agent can point it out when suggesting how to reach a goal.

Replace this function with a real data source (database, CSV import, banking API) to make the assistant useful beyond a demo.

## Design notes

- **`root_agent` is required.** ADK looks for a variable named `root_agent` in the package to know which agent to start. Here it is `finance_assistance_agent`.
- **Why `AgentTool`?** The code comments record two ADK constraints: built-in tools (like `google_search`) can't be mixed with custom function tools in the same agent, and an agent can use only one built-in tool at a time. Putting `google_search` in its own agent and wrapping that agent as a tool gives the root agent both capabilities. Newer ADK releases may relax these limits, so re-check them against the ADK version you have installed (currently 2.12.0).
- **Agent-as-tool vs. sub-agent.** With `AgentTool`, the root agent calls the specialist like a function and gets one result back, and the root keeps control of the conversation. The specialist does not talk to the user directly, and it only sees what the root passes in the request. The root prompt therefore tells the model to put the goal, timeline, risk tolerance and figures into every delegation. If the specialist is missing something, it replies with `MISSING INFORMATION:` and the root asks the user.
- **No curly braces in instructions.** ADK treats `{name}` inside an agent's `instruction` as a session-state placeholder, so keep braces out of the prompts.

## Roadmap

Planned and suggested improvements:

- Replace the mock data with a real data source and per-user state.
- Split the work into workflow agents (`SequentialAgent` / `ParallelAgent`): budget analysis, market research, goal planning.
- Add `adk eval` test cases for routing and answer quality.
- Move the model name and other settings to environment variables.

## Disclaimer

This project is for learning and demonstration. Responses are generated by an AI model and may be inaccurate or out of date. They are not financial, investment, tax or legal advice.

## Tech stack

[Google ADK](https://google.github.io/adk-docs/) · Gemini · Google Search grounding · python-dotenv
