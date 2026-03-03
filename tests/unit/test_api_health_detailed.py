from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_health_detailed_schema_aligned_ok_response(monkeypatch) -> None:
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
    def _raise_response(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.api.main.DetailedHealthResponse", _raise_response)

    response = client.get("/health/detailed")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "health_details_unavailable"
