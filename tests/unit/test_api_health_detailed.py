from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def _reset_detailed_health_cache(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.main._detailed_health_cache", None)
    monkeypatch.setattr("backend.api.main._detailed_health_cache_timestamp", 0.0)


def test_health_detailed_cache_within_ttl_and_recompute_after_ttl(monkeypatch) -> None:
    _reset_detailed_health_cache(monkeypatch)

    class _DetectedType:
        value = "CPU_ONLY"

    compute_counter = {"count": 0}

    def _counted_system_info(self):
        compute_counter["count"] += 1
        return {"cpu_cores": 8, "total_ram_gb": 16.0, "gpu_info": []}

    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_system_info",
        _counted_system_info,
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.detect_hardware_type",
        lambda self: _DetectedType(),
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_hardware_profile",
        lambda self: "medium",
    )
    monkeypatch.setattr(
        "backend.models.model_registry.ModelRegistry.select_model",
        lambda self, profile, hardware, role: {"id": "cache-test-model"},
    )

    class _FakeCacheClient:
        def health_check(self):
            return {"enabled": True, "connected": True, "message": "Connected"}

    monkeypatch.setattr(
        "backend.cache.redis_client.create_default_redis_client",
        lambda: _FakeCacheClient(),
    )

    # Deterministic monotonic timeline:
    # call1 now=100.0 (compute), call2 now=110.0 (within TTL -> cached), call3 now=131.0 (expired -> recompute)
    monotonic_values = iter([100.0, 110.0, 131.0])
    monkeypatch.setattr("backend.api.main._monotonic_now", lambda: next(monotonic_values))

    response1 = client.get("/health/detailed")
    assert response1.status_code == 200
    body1 = response1.json()

    response2 = client.get("/health/detailed")
    assert response2.status_code == 200
    body2 = response2.json()

    assert body1 == body2
    assert compute_counter["count"] == 1

    response3 = client.get("/health/detailed")
    assert response3.status_code == 200
    body3 = response3.json()

    assert body3 == body1
    assert compute_counter["count"] == 2


def test_health_detailed_schema_aligned_ok_response(monkeypatch) -> None:
    _reset_detailed_health_cache(monkeypatch)

    class _DetectedType:
        value = "CPU_ONLY"

    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_system_info",
        lambda self: {"cpu_cores": 8, "total_ram_gb": 32.0, "gpu_info": []},
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.detect_hardware_type",
        lambda self: _DetectedType(),
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_hardware_profile",
        lambda self: "medium",
    )

    monkeypatch.setattr(
        "backend.models.model_registry.ModelRegistry.select_model",
        lambda self, profile, hardware, role: {"id": "test-mini"},
    )

    class _FakeCacheClient:
        def health_check(self):
            return {"enabled": True, "connected": True, "message": "Connected"}

    monkeypatch.setattr(
        "backend.cache.redis_client.create_default_redis_client",
        lambda: _FakeCacheClient(),
    )

    response = client.get("/health/detailed")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "JARVISv5-backend"
    assert set(["profile", "type", "cpu_count", "memory_gb"]).issubset(body["hardware"].keys())
    assert set(["selected", "profile", "role"]).issubset(body["model"].keys())
    assert set(["enabled", "connected"]).issubset(body["cache"].keys())


def test_health_detailed_degraded_when_cache_disconnected(monkeypatch) -> None:
    _reset_detailed_health_cache(monkeypatch)

    class _DetectedType:
        value = "CPU_ONLY"

    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_system_info",
        lambda self: {"cpu_cores": 4, "total_ram_gb": 16.0, "gpu_info": []},
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.detect_hardware_type",
        lambda self: _DetectedType(),
    )
    monkeypatch.setattr(
        "backend.models.hardware_profiler.HardwareService.get_hardware_profile",
        lambda self: "light",
    )
    monkeypatch.setattr(
        "backend.models.model_registry.ModelRegistry.select_model",
        lambda self, profile, hardware, role: {"id": "test-mini"},
    )

    class _FakeCacheClient:
        def health_check(self):
            return {"enabled": True, "connected": False, "message": "Connection unavailable"}

    monkeypatch.setattr(
        "backend.cache.redis_client.create_default_redis_client",
        lambda: _FakeCacheClient(),
    )

    response = client.get("/health/detailed")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["cache"]["enabled"] is True
    assert body["cache"]["connected"] is False


def test_health_detailed_unavailable_returns_500(monkeypatch) -> None:
    _reset_detailed_health_cache(monkeypatch)

    def _raise_response(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.api.main.DetailedHealthResponse", _raise_response)

    response = client.get("/health/detailed")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "health_details_unavailable"
