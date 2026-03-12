from __future__ import annotations

from pydantic import BaseModel, Field

from backend.config.settings import Settings
from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger


class SearchPolicyRequest(BaseModel):
    allow_external: bool = False
    purpose: str = "search"
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    date_key: str | None = None
    task_id: str | None = None
    provider_is_external: bool = True
    provider_is_paid: bool = False
    allow_paid_search: bool | None = None
    paid_key_configured: bool | None = None


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

    provider_is_external = bool(request.provider_is_external)
    provider_is_paid = bool(request.provider_is_paid)
    settings = Settings()
    allow_paid_search = (
        bool(request.allow_paid_search)
        if request.allow_paid_search is not None
        else bool(settings.ALLOW_PAID_SEARCH)
    )
    paid_key_configured = (
        bool(request.paid_key_configured)
        if request.paid_key_configured is not None
        else bool(str(settings.TAVILY_API_KEY).strip())
    )

    def _decision(
        *,
        allow: bool,
        code: str,
        reason: str,
        path: str,
        remaining_budget_usd: float,
    ) -> tuple[bool, dict[str, object]]:
        return allow, {
            "allow": allow,
            "code": code,
            "reason": reason,
            "path": path,
            "provider_is_external": provider_is_external,
            "provider_is_paid": provider_is_paid,
            "allow_paid_search": allow_paid_search,
            "paid_key_configured": paid_key_configured,
            "remaining_budget_usd": remaining_budget_usd,
            "estimated_cost_usd": estimated_cost,
            "date_key": date_key,
        }

    if estimated_cost < 0.0 or config.daily_limit_usd < 0.0:
        return _decision(
            allow=False,
            code="validation_error",
            reason="invalid budget input",
            path="blocked",
            remaining_budget_usd=0.0,
        )

    remaining = budget_ledger.remaining_budget_usd(date_key, config.daily_limit_usd)

    if not provider_is_external:
        return _decision(
            allow=True,
            code="ok",
            reason="allowed",
            path="free",
            remaining_budget_usd=remaining,
        )

    if not request.allow_external:
        return _decision(
            allow=False,
            code="permission_denied",
            reason="external search not allowed",
            path="blocked",
            remaining_budget_usd=remaining,
        )

    if provider_is_paid and not allow_paid_search:
        return _decision(
            allow=False,
            code="permission_denied",
            reason="paid search not allowed",
            path="blocked",
            remaining_budget_usd=remaining,
        )

    if provider_is_paid and not paid_key_configured:
        return _decision(
            allow=False,
            code="provider_unavailable",
            reason="paid provider key not configured",
            path="blocked",
            remaining_budget_usd=remaining,
        )

    if not budget_ledger.can_spend(estimated_cost, date_key, config.daily_limit_usd):
        return _decision(
            allow=False,
            code="budget_exceeded",
            reason="daily budget exceeded",
            path="blocked",
            remaining_budget_usd=remaining,
        )

    return _decision(
        allow=True,
        code="ok",
        reason="allowed",
        path="paid" if provider_is_paid else "free",
        remaining_budget_usd=remaining,
    )
