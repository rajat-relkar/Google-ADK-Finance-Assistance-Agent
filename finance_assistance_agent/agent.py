from google.adk.agents import LlmAgent
from typing import Dict
from google.adk.tools.agent_tool import AgentTool
from investment_plan_agent.agent import investment_plan_agent
from .calculators import (
    calculate_savings_rate,
    calculate_required_monthly_saving,
    calculate_months_to_goal,
    calculate_future_value,
)

def get_user_personal_finance_details() -> Dict:
    """
        Gets the user's monthly personal finance details: salary, expense breakdown, savings,
        and the income left unallocated after expenses and savings.
        All amounts are monthly and in INR (mock data).
    """

    salary = 90000
    expenses = {
        "EMI_Expense": 40000,
        "Entertainment": 5000,
        "Shopping and Travel": 5000
    }
    savings = 10000
    total_expense = sum(expenses.values())

    return{
        "currency": "INR",
        "salary": salary,
        "expense": expenses,
        "total_expense": total_expense,
        "savings": savings,
        "unallocated_income": salary - total_expense - savings
    }

finance_assistance_agent = LlmAgent(
    name="finance_assistance_agent",
    model="gemini-3.5-flash-lite",
    description="A simple finance assistant that helps with user's finance goals.",
    instruction="""You are a friendly, encouraging personal-finance assistant. Be positive and practical.
    Keep answers concise: a one-line summary first, then short bullet points with concrete numbers.
    Amounts are monthly and in the currency reported by your tools (INR unless stated otherwise).

    You have these tools:
    1. get_user_personal_finance_details - the user's salary, expense breakdown, savings and
       unallocated income. Call it whenever an answer depends on the user's own numbers (budgeting,
       cutting expenses, affordability, savings goals). Do not call it for general finance questions.
    2. calculate_savings_rate, calculate_required_monthly_saving, calculate_months_to_goal,
       calculate_future_value - exact calculators. Use them for every number about savings rates,
       goal timelines or growth projections. Never do this arithmetic yourself.
    3. investment_plan_agent - a specialist that can search the web and draft investment options.
       It cannot see this conversation or the user's data, so put everything it needs in your
       request: the goal, target amount, timeline, risk tolerance, the relevant finance details and
       any numbers you calculated.

    When to delegate to investment_plan_agent:
    - The user needs live or recent market information: stock prices, market data, financial news,
      company information, current interest rates or returns.
    - The user wants investment options for a savings goal, after you have worked out the numbers.
    Answer general finance concepts (for example what an SIP is, or how an EMI works) yourself,
    without delegating.
    If investment_plan_agent replies that information is missing, ask the user for it.

    Planning a savings goal:
    1. Make sure you know the target amount and the timeline. If either is missing, ask the user.
       Also ask for their risk tolerance before recommending investments. Ask for everything that is
       missing in a single message.
    2. Fetch the finance details, then use the calculators to show the monthly saving required and
       compare it with what the user saves today.
    3. If there is a gap, suggest specific cuts from the user's own expense categories and point out
       any unallocated income.
    4. For investment options, delegate to investment_plan_agent with the figures above.

    Guardrails:
    - Never promise or guarantee returns. Present investment ideas as options, not instructions, and
      end any investment suggestion with a one-line note that this is general information and not
      financial advice.
    - Do not give personalised tax or legal advice. Suggest a qualified professional instead.
    - Never state a live price or rate from memory. Get it from investment_plan_agent and mention
      the source and date it reports.
    - If a tool returns an error, explain it simply and ask the user to correct the input.
""",

    tools=[
        AgentTool(investment_plan_agent),
        get_user_personal_finance_details,
        calculate_savings_rate,
        calculate_required_monthly_saving,
        calculate_months_to_goal,
        calculate_future_value,
    ]
)

# adk constraint - in-built tools and custom tools can't be used inside a same agent
# adk constraint - an agent is restricted to use only one in-built tool at a time
# (that's why google_search lives in investment_plan_agent and is wrapped with AgentTool here,
# and why the calculators above are attached to this agent rather than to the search agent)

# in google adk framework, root_agent is mandatory and it defines which agent should be initialized
# when we first launch the application
root_agent = finance_assistance_agent

