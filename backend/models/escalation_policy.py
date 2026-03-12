from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from backend.config.api_keys import ApiKeyRegistry, SUPPORTED_PROVIDERS


class EscalationTrigger(str, Enum):
    LOCAL_MODEL_MISSING = "local_model_missing"
    LOCAL_MODEL_PATH_ERROR = "local_model_path_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class EscalationDecisionCode(str, Enum):
    PERMISSION_DENIED = "permission_denied"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    PROVIDER_UNSUPPORTED = "provider_unsupported"
    PROVIDER_KEY_MISSING = "provider_key_missing"
    BUDGET_NOT_ALLOCATED = "budget_not_allocated"
    BUDGET_EXCEEDED = "budget_exceeded"
    OK = "ok"


class EscalationPath(str, Enum):
    LOCAL = "local"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


ESCALATION_REASON_BY_CODE: dict[EscalationDecisionCode, str] = {
    EscalationDecisionCode.PERMISSION_DENIED: "model escalation disabled",
    EscalationDecisionCode.PROVIDER_NOT_CONFIGURED: "escalation provider not configured",
    EscalationDecisionCode.PROVIDER_UNSUPPORTED: "escalation provider unsupported",
    EscalationDecisionCode.PROVIDER_KEY_MISSING: "escalation provider key missing",
    EscalationDecisionCode.BUDGET_NOT_ALLOCATED: "escalation budget not allocated",
    EscalationDecisionCode.BUDGET_EXCEEDED: "escalation budget exceeded",
    EscalationDecisionCode.OK: "allowed",
}


class EscalationPolicyRequest(BaseModel):
    trigger: EscalationTrigger
    allow_escalation: bool = False
    provider: str = ""
    budget_usd: float = Field(default=0.0, ge=0.0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)


def _decision(
    *,
    allow: bool,
    code: EscalationDecisionCode,
    path: EscalationPath,
    request: EscalationPolicyRequest,
    provider: str,
    provider_supported: bool,
    provider_configured: bool,
) -> tuple[bool, dict[str, object]]:
    provider_key_configured = provider_supported and provider_configured
    return allow, {
        "allow": allow,
        "code": code.value,
        "reason": ESCALATION_REASON_BY_CODE[code],
        "path": path.value,
        "trigger": request.trigger.value,
        "provider": provider,
        "provider_supported": provider_supported,
        "provider_configured": provider_configured,
        "provider_key_configured": provider_key_configured,
        "budget_usd": float(request.budget_usd),
        "estimated_cost_usd": float(request.estimated_cost_usd),
    }


def decide_escalation(request: EscalationPolicyRequest) -> tuple[bool, dict[str, object]]:
    provider = str(request.provider).strip().lower()
    provider_supported = provider in SUPPORTED_PROVIDERS
    configured_providers = set(ApiKeyRegistry().get_configured_providers())
    provider_configured = provider in configured_providers

    if not request.allow_escalation:
        return _decision(
            allow=False,
            code=EscalationDecisionCode.PERMISSION_DENIED,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    if not provider:
        return _decision(
            allow=False,
            code=EscalationDecisionCode.PROVIDER_NOT_CONFIGURED,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    if not provider_supported:
        return _decision(
            allow=False,
            code=EscalationDecisionCode.PROVIDER_UNSUPPORTED,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    if not provider_configured:
        return _decision(
            allow=False,
            code=EscalationDecisionCode.PROVIDER_KEY_MISSING,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    if float(request.budget_usd) <= 0.0:
        return _decision(
            allow=False,
            code=EscalationDecisionCode.BUDGET_NOT_ALLOCATED,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    if float(request.estimated_cost_usd) > float(request.budget_usd):
        return _decision(
            allow=False,
            code=EscalationDecisionCode.BUDGET_EXCEEDED,
            path=EscalationPath.BLOCKED,
            request=request,
            provider=provider,
            provider_supported=provider_supported,
            provider_configured=provider_configured,
        )

    return _decision(
        allow=True,
        code=EscalationDecisionCode.OK,
        path=EscalationPath.ESCALATED,
        request=request,
        provider=provider,
        provider_supported=provider_supported,
        provider_configured=provider_configured,
    )


class EscalationProviderBase(ABC):
    name: str

    @abstractmethod
    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        raise NotImplementedError


class StubEscalationProvider(EscalationProviderBase):
    name = "stub"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = prompt
        _ = max_tokens
        _ = seed
        return True, "stub_escalation_output", ""
