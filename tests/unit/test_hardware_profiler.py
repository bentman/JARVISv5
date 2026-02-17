from backend.models.hardware_profiler import HardwareService, HardwareType, ResourceManager


def test_hardware_service_system_info_and_profiles() -> None:
    service = HardwareService()

    info = service.get_system_info()
    assert isinstance(info, dict)
    assert isinstance(info.get("cpu_cores"), int)
    assert info["cpu_cores"] > 0
    assert isinstance(info.get("total_ram_gb"), float)
    assert isinstance(info.get("gpu_info"), list)

    detected = service.detect_hardware_type()
    assert isinstance(detected, HardwareType)
    assert detected in set(HardwareType)

    profile = service.get_hardware_profile()
    assert isinstance(profile, str)
    assert profile in {"light", "medium", "heavy", "npu-optimized"}


def test_refresh_hardware_info_populates_internal_state() -> None:
    service = HardwareService()
    service.refresh_hardware_info()

    assert service._cpu_info
    assert "logical_cores" in service._cpu_info
    assert "physical_cores" in service._cpu_info
    assert "architecture" in service._cpu_info

    assert service._memory_info
    assert "total_ram_gb" in service._memory_info
    assert "available_ram_gb" in service._memory_info


def test_get_optimized_model_config_for_each_hardware_type() -> None:
    service = HardwareService()
    expected_providers = {
        HardwareType.GPU_CUDA: "cuda",
        HardwareType.NPU_APPLE: "gpu",
        HardwareType.NPU_INTEL: "npu",
        HardwareType.QUALCOMM_NPU: "npu",
        HardwareType.GPU_GENERAL: "gpu",
        HardwareType.CPU_ONLY: "cpu",
    }

    for hardware_type, provider in expected_providers.items():
        cfg = service.get_optimized_model_config(hardware_type)
        assert isinstance(cfg, dict)
        assert set(cfg.keys()) == {"batch_size", "quantization", "precision", "provider"}
        assert cfg["provider"] == provider


def test_get_hardware_state_shape_and_types() -> None:
    service = HardwareService()
    state = service.get_hardware_state()

    assert isinstance(state, dict)
    assert isinstance(state["cpu_usage"], float)
    assert isinstance(state["memory_available_gb"], float)
    assert isinstance(state["gpu_usage"], float)
    assert isinstance(state["available_tiers"], list)
    assert isinstance(state["current_load"], float)
    assert "cpu" in state["available_tiers"]


def test_resource_manager_allocate_and_release_memory() -> None:
    manager = ResourceManager()
    manager.allocate_memory("test", "cpu", 100)

    assert "test" in manager.allocations
    assert manager.allocations["test"]["requested_mb"] == 100

    released = manager.release_memory("test")
    assert released is True
    assert "test" not in manager.allocations


def test_resource_manager_check_resource_exhaustion_runs() -> None:
    manager = ResourceManager()
    status = manager.check_resource_exhaustion()
    assert status in {
        None,
        "critical_memory_exhaustion",
        "high_memory_pressure",
        "cpu_exhaustion",
    }
