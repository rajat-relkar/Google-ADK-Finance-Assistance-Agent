"""Deterministic finance calculators exposed to the root agent as function tools.

LLMs are unreliable at multi-step arithmetic, so every figure the assistant quotes about
savings rates, goal timelines or growth projections should come from these functions.

ADK conventions followed here: each tool returns a dict with a "status" key ("success" or
"error"), and the docstring doubles as the tool description the model sees.

Projection assumptions (shared by the growth-based tools): monthly compounding at
annual_return_percent / 12, with each monthly contribution made at the end of the month.
"""
import math
from typing import Dict


def _error(message: str) -> Dict:
    return {"status": "error", "error_message": message}


def _monthly_rate(annual_return_percent: float) -> float:
    return annual_return_percent / 100 / 12


def calculate_savings_rate(monthly_income: float, monthly_savings: float) -> Dict:
    """Calculates what percentage of monthly income the user saves.

    Args:
        monthly_income: Monthly income (salary). Must be greater than 0.
        monthly_savings: Amount saved per month. Must be 0 or more.

    Returns:
        A dict with status and savings_rate_percent (0-100 when savings do not exceed income).
    """
    if monthly_income <= 0:
        return _error("monthly_income must be greater than 0.")
    if monthly_savings < 0:
        return _error("monthly_savings cannot be negative.")

    return {
        "status": "success",
        "monthly_income": monthly_income,
        "monthly_savings": monthly_savings,
        "savings_rate_percent": round(monthly_savings / monthly_income * 100, 2),
    }


def calculate_required_monthly_saving(
    target_amount: float,
    months: int,
    current_savings: float = 0.0,
    annual_return_percent: float = 0.0,
) -> Dict:
    """Calculates how much must be saved every month to reach a goal by a deadline.

    Args:
        target_amount: The goal amount. Must be greater than 0.
        months: Number of months until the goal date. Must be greater than 0.
        current_savings: Amount already set aside for this goal. Defaults to 0.
        annual_return_percent: Expected annual return in percent (e.g. 7 for 7%). Use 0 for
            plain saving with no growth. Defaults to 0.

    Returns:
        A dict with status, required_monthly_saving, total_contributions and
        expected_growth (the part of the target covered by returns). If current savings
        alone will already reach the target, required_monthly_saving is 0 and
        already_on_track is true.
    """
    if target_amount <= 0:
        return _error("target_amount must be greater than 0.")
    if months <= 0:
        return _error("months must be greater than 0.")
    if current_savings < 0:
        return _error("current_savings cannot be negative.")
    if annual_return_percent < 0:
        return _error("annual_return_percent cannot be negative.")

    rate = _monthly_rate(annual_return_percent)
    growth_factor = (1 + rate) ** months
    shortfall = target_amount - current_savings * growth_factor

    if shortfall <= 0:
        return {
            "status": "success",
            "already_on_track": True,
            "required_monthly_saving": 0.0,
            "total_contributions": 0.0,
            "expected_growth": round(target_amount - current_savings, 2),
        }

    if rate == 0:
        required = shortfall / months
    else:
        required = shortfall * rate / (growth_factor - 1)

    total_contributions = required * months
    return {
        "status": "success",
        "already_on_track": False,
        "required_monthly_saving": round(required, 2),
        "total_contributions": round(total_contributions, 2),
        "expected_growth": round(target_amount - current_savings - total_contributions, 2),
    }


def calculate_months_to_goal(
    target_amount: float,
    monthly_saving: float,
    current_savings: float = 0.0,
    annual_return_percent: float = 0.0,
) -> Dict:
    """Calculates how long it takes to reach a goal at a given monthly saving.

    Args:
        target_amount: The goal amount. Must be greater than 0.
        monthly_saving: Amount saved per month. Must be 0 or more.
        current_savings: Amount already set aside for this goal. Defaults to 0.
        annual_return_percent: Expected annual return in percent (e.g. 7 for 7%). Use 0 for
            plain saving with no growth. Defaults to 0.

    Returns:
        A dict with status, months_to_goal (whole months, rounded up), years_and_months
        (readable text) and years (decimal). Returns an error if the goal can never be
        reached with the given inputs.
    """
    if target_amount <= 0:
        return _error("target_amount must be greater than 0.")
    if monthly_saving < 0:
        return _error("monthly_saving cannot be negative.")
    if current_savings < 0:
        return _error("current_savings cannot be negative.")
    if annual_return_percent < 0:
        return _error("annual_return_percent cannot be negative.")

    if current_savings >= target_amount:
        months = 0
    elif monthly_saving == 0 and current_savings == 0:
        return _error("The goal cannot be reached with no savings and no monthly saving.")
    else:
        rate = _monthly_rate(annual_return_percent)
        if rate == 0:
            if monthly_saving == 0:
                return _error("The goal cannot be reached with no monthly saving and no returns.")
            exact_months = (target_amount - current_savings) / monthly_saving
        else:
            # Solve current*(1+r)^n + saving*((1+r)^n - 1)/r = target for n.
            annuity = monthly_saving / rate
            exact_months = math.log((target_amount + annuity) / (current_savings + annuity)) / math.log(1 + rate)
        # Subtract a tiny epsilon so floating-point noise does not add a spurious month.
        months = math.ceil(exact_months - 1e-9)

    years, remaining_months = divmod(months, 12)
    return {
        "status": "success",
        "months_to_goal": months,
        "years_and_months": f"{years} years {remaining_months} months",
        "years": round(months / 12, 2),
    }


def calculate_future_value(
    monthly_contribution: float,
    years: float,
    annual_return_percent: float = 0.0,
    initial_amount: float = 0.0,
) -> Dict:
    """Projects how much a regular monthly investment or saving grows to over time.

    Args:
        monthly_contribution: Amount added every month. Must be 0 or more.
        years: Investment horizon in years. Must be greater than 0.
        annual_return_percent: Expected annual return in percent (e.g. 7 for 7%). Use 0 for
            plain saving with no growth. Defaults to 0.
        initial_amount: Lump sum invested at the start. Defaults to 0.

    Returns:
        A dict with status, future_value, total_contributed (initial amount plus all monthly
        contributions) and growth_earned (future value minus total contributed).
    """
    if monthly_contribution < 0:
        return _error("monthly_contribution cannot be negative.")
    if years <= 0:
        return _error("years must be greater than 0.")
    if initial_amount < 0:
        return _error("initial_amount cannot be negative.")
    if annual_return_percent < 0:
        return _error("annual_return_percent cannot be negative.")

    months = round(years * 12)
    if months < 1:
        return _error("years must cover at least one month.")

    rate = _monthly_rate(annual_return_percent)
    growth_factor = (1 + rate) ** months
    contributions_value = monthly_contribution * months if rate == 0 else monthly_contribution * (growth_factor - 1) / rate

    future_value = initial_amount * growth_factor + contributions_value
    total_contributed = initial_amount + monthly_contribution * months
    return {
        "status": "success",
        "months": months,
        "future_value": round(future_value, 2),
        "total_contributed": round(total_contributed, 2),
        "growth_earned": round(future_value - total_contributed, 2),
    }
