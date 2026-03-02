from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field


class SearchBudgetConfig(BaseModel):
    daily_limit_usd: float = Field(default=0.0, ge=0.0)
    per_call_estimate_usd: float = Field(default=0.0, ge=0.0)
    rollover: bool = False


class SearchBudgetLedger:
    def __init__(
        self,
        path: str | Path = "data/search/budget.json",
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path)
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._ledger: dict[str, Any] = self.load()

    @staticmethod
    def _empty_ledger() -> dict[str, Any]:
        return {"spend_by_day": {}, "events": []}

    @staticmethod
    def _sanitize_ledger(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return SearchBudgetLedger._empty_ledger()

        spend_raw = raw.get("spend_by_day", {})
        spend_by_day: dict[str, float] = {}
        if isinstance(spend_raw, dict):
            for key, value in spend_raw.items():
                if not isinstance(key, str):
                    continue
                try:
                    amount = float(value)
                except (TypeError, ValueError):
                    continue
                if amount < 0.0:
                    continue
                spend_by_day[key] = amount

        events_raw = raw.get("events", [])
        events: list[dict[str, Any]] = []
        if isinstance(events_raw, list):
            for item in events_raw:
                if isinstance(item, dict):
                    events.append(dict(item))

        return {"spend_by_day": spend_by_day, "events": events}

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_ledger()

        try:
            text = self.path.read_text(encoding="utf-8")
            parsed = json.loads(text)
            return self._sanitize_ledger(parsed)
        except Exception:
            return self._empty_ledger()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._sanitize_ledger(self._ledger)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def today_key(self) -> str:
        now = self._now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).date().isoformat()

    def get_spent(self, date_key: str) -> float:
        spend_by_day = self._ledger.get("spend_by_day", {})
        if not isinstance(spend_by_day, dict):
            return 0.0
        raw = spend_by_day.get(date_key, 0.0)
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            return 0.0
        return amount if amount >= 0.0 else 0.0

    def remaining_budget_usd(self, date_key: str, daily_limit_usd: float) -> float:
        spent = self.get_spent(date_key)
        remaining = float(daily_limit_usd) - spent
        return remaining if remaining > 0.0 else 0.0

    def can_spend(self, amount_usd: float, date_key: str, daily_limit_usd: float) -> bool:
        if amount_usd < 0.0 or daily_limit_usd < 0.0:
            return False
        if daily_limit_usd == 0.0:
            return True
        return self.get_spent(date_key) + float(amount_usd) <= float(daily_limit_usd)

    def record_spend(
        self,
        amount_usd: float,
        date_key: str,
        provider: str,
        task_id: str | None = None,
    ) -> None:
        if amount_usd < 0.0:
            raise ValueError("amount_usd must be >= 0")

        spend_by_day = self._ledger.setdefault("spend_by_day", {})
        if not isinstance(spend_by_day, dict):
            spend_by_day = {}
            self._ledger["spend_by_day"] = spend_by_day

        current = self.get_spent(date_key)
        spend_by_day[date_key] = current + float(amount_usd)

        events = self._ledger.setdefault("events", [])
        if not isinstance(events, list):
            events = []
            self._ledger["events"] = events

        now = self._now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        events.append(
            {
                "timestamp": now.astimezone(timezone.utc).isoformat(),
                "date_key": date_key,
                "amount_usd": float(amount_usd),
                "provider": str(provider),
                "task_id": task_id,
            }
        )
        self.save()
