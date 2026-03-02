from __future__ import annotations

from pydantic import BaseModel, Field

from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger


class SearchPolicyRequest(BaseModel):
    allow_external: bool = False
    purpose: str = "search"
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    date_key: str | None = None
    task_id: str | None = None


def decide_external_search(
    request: SearchPolicyRequest,
    budget_ledger: SearchBudgetLedger,
    config: SearchBudgetConfig,
) -> tuple[bool, dict[str, object]]:
    date_key = request.date_key or budget_ledger.today_key()

    estimated_cost = (
        float(request.estimated_cost_usd)
        if request.estimated_cost_usd is not None
        else float(config.per_call_estimate_usd)
    )

    if estimated_cost < 0.0 or config.daily_limit_usd < 0.0:
        return False, {
            "allow": False,
            "code": "validation_error",
            "reason": "invalid budget input",
            "remaining_budget_usd": 0.0,
            "estimated_cost_usd": max(0.0, estimated_cost),
            "date_key": date_key,
        }

    remaining = budget_ledger.remaining_budget_usd(date_key, config.daily_limit_usd)

    if not request.allow_external:
        return False, {
            "allow": False,
            "code": "permission_denied",
            "reason": "external search not allowed",
            "remaining_budget_usd": remaining,
            "estimated_cost_usd": estimated_cost,
            "date_key": date_key,
        }

    if not budget_ledger.can_spend(estimated_cost, date_key, config.daily_limit_usd):
        return False, {
            "allow": False,
            "code": "budget_exceeded",
            "reason": "daily budget exceeded",
            "remaining_budget_usd": remaining,
            "estimated_cost_usd": estimated_cost,
            "date_key": date_key,
        }

    return True, {
        "allow": True,
        "code": "ok",
        "reason": "allowed",
        "remaining_budget_usd": remaining,
        "estimated_cost_usd": estimated_cost,
        "date_key": date_key,
    }
