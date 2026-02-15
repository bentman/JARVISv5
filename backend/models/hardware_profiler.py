from enum import Enum
import platform
from typing import Any

import psutil


class HardwareType(str, Enum):
    CPU_ONLY = "CPU_ONLY"
    GPU_CUDA = "GPU_CUDA"
    GPU_GENERAL = "GPU_GENERAL"
    NPU_APPLE = "NPU_APPLE"
    NPU_INTEL = "NPU_INTEL"


class HardwareService:
    def __init__(self) -> None:
        self._cpu_info: dict[str, Any] = {}
        self._gpu_info: list[dict[str, Any]] = []
        self._memory_info: dict[str, Any] = {}
        self._accel_providers: list[str] = []
        self.refresh_hardware_info()

    def _safe_cpu_info(self) -> dict[str, Any]:
        try:
            freq = psutil.cpu_freq()
            max_mhz = float(freq.max) if freq is not None else 0.0
        except Exception:
            max_mhz = 0.0

        try:
            logical = int(psutil.cpu_count(logical=True) or 1)
        except Exception:
            logical = 1

        try:
            physical = int(psutil.cpu_count(logical=False) or logical)
        except Exception:
            physical = logical

        return {
            "logical_cores": logical,
            "physical_cores": physical,
            "max_frequency_mhz": max_mhz,
            "architecture": platform.machine() or "unknown",
        }

    def _safe_memory_info(self) -> dict[str, Any]:
        try:
            vm = psutil.virtual_memory()
            return {
                "total_ram_gb": round(vm.total / (1024**3), 2),
                "available_ram_gb": round(vm.available / (1024**3), 2),
                "percent": float(vm.percent),
            }
        except Exception:
            return {
                "total_ram_gb": 0.0,
                "available_ram_gb": 0.0,
                "percent": 0.0,
            }

    def _runtime_providers(self) -> list[str]:
        try:
            import onnxruntime as ort  # type: ignore

            providers = ort.get_available_providers()
            return [str(p) for p in providers]
        except Exception:
            return []

    def refresh_hardware_info(self) -> None:
        self._cpu_info = self._safe_cpu_info()
        self._memory_info = self._safe_memory_info()
        self._accel_providers = self._runtime_providers()

        gpu_info: list[dict[str, Any]] = []
        try:
            import GPUtil  # type: ignore

            for gpu in GPUtil.getGPUs():
                gpu_info.append(
                    {
                        "name": gpu.name,
                        "provider": "gputil",
                        "vendor": self._infer_gpu_vendor(gpu.name),
                        "memory_total_mb": float(getattr(gpu, "memoryTotal", 0.0)),
                        "load": float(getattr(gpu, "load", 0.0)),
                    }
                )
        except Exception:
            pass

        if not gpu_info:
            provider_map = {
                "cudaexecutionprovider": ("nvidia-provider", "nvidia"),
                "coremlexecutionprovider": ("coreml-provider", "apple"),
                "dmlexecutionprovider": ("directml-provider", "microsoft"),
                "rocmexecutionprovider": ("rocm-provider", "amd"),
            }
            for provider in self._accel_providers:
                key = provider.lower()
                if key in provider_map:
                    name, vendor = provider_map[key]
                    gpu_info.append(
                        {
                            "name": name,
                            "provider": "onnxruntime",
                            "vendor": vendor,
                            "memory_total_mb": 0.0,
                            "load": 0.0,
                        }
                    )

        self._gpu_info = gpu_info

    def _infer_gpu_vendor(self, gpu_name: str) -> str:
        name = gpu_name.lower()
        if "nvidia" in name:
            return "nvidia"
        if "amd" in name or "radeon" in name:
            return "amd"
        if "intel" in name:
            return "intel"
        if "apple" in name:
            return "apple"
        return "unknown"

    def _detect_cuda_gpu(self) -> bool:
        try:
            import torch  # type: ignore

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def _detect_apple_npu(self) -> bool:
        try:
            import torch  # type: ignore

            mps_available = bool(torch.backends.mps.is_available())
        except Exception:
            mps_available = False

        system = platform.system().lower()
        machine = platform.machine().lower()
        return mps_available and system == "darwin" and machine in {"arm64", "aarch64"}

    def _detect_intel_npu(self) -> bool:
        try:
            import openvino as ov  # type: ignore

            core = ov.Core()
            devices = [device.upper() for device in core.available_devices]
            if any("NPU" in device for device in devices):
                return True
        except Exception:
            pass

        # Best-effort provider hints path.
        try:
            providers = [p.lower() for p in self._accel_providers]
            if any("openvino" in p or "npu" in p for p in providers):
                return True
        except Exception:
            pass

        # Explicit branch retained for future Intel NPU signals/extensions
        # even when OpenVINO is unavailable or does not expose NPU directly.
        return False

    def _detect_general_gpu(self) -> list[dict[str, Any]]:
        gpu_info: list[dict[str, Any]] = []

        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                count = int(torch.cuda.device_count())
                for index in range(count):
                    gpu_info.append({"name": torch.cuda.get_device_name(index), "provider": "torch"})
                return gpu_info
        except Exception:
            pass

        try:
            import GPUtil  # type: ignore

            for gpu in GPUtil.getGPUs():
                gpu_info.append({"name": gpu.name, "provider": "gputil"})
        except Exception:
            pass

        return gpu_info

    def get_system_info(self) -> dict[str, Any]:
        self.refresh_hardware_info()
        return {
            "cpu_cores": int(self._cpu_info.get("logical_cores", 0)),
            "total_ram_gb": float(self._memory_info.get("total_ram_gb", 0.0)),
            "gpu_info": list(self._gpu_info),
        }

    def detect_hardware_type(self) -> HardwareType:
        self.refresh_hardware_info()

        # 1) GPU_CUDA
        if self._detect_cuda_gpu():
            return HardwareType.GPU_CUDA

        # 2) NPU_APPLE
        if self._detect_apple_npu():
            return HardwareType.NPU_APPLE

        # 3) NPU_INTEL (best effort)
        if self._detect_intel_npu():
            return HardwareType.NPU_INTEL

        # 4) GPU_GENERAL
        if self._gpu_info or self._detect_general_gpu():
            return HardwareType.GPU_GENERAL

        # 5) CPU_ONLY
        return HardwareType.CPU_ONLY

    def get_hardware_profile(self) -> str:
        hardware_type = self.detect_hardware_type()
        if hardware_type in {HardwareType.NPU_APPLE, HardwareType.NPU_INTEL}:
            return "NPU-optimized"

        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        if total_ram_gb >= 32:
            return "Heavy"
        if total_ram_gb >= 16:
            return "Medium"
        return "Light"

    def get_optimized_model_config(self, model_type: HardwareType | None = None) -> dict[str, Any]:
        hardware_type = model_type or self.detect_hardware_type()

        mapping: dict[HardwareType, dict[str, Any]] = {
            HardwareType.GPU_CUDA: {
                "batch_size": 4,
                "quantization": "int8",
                "precision": "fp16",
                "provider": "cuda",
            },
            HardwareType.NPU_APPLE: {
                "batch_size": 2,
                "quantization": "int8",
                "precision": "fp16",
                "provider": "gpu",
            },
            HardwareType.NPU_INTEL: {
                "batch_size": 1,
                "quantization": "int8",
                "precision": "int8",
                "provider": "npu",
            },
            HardwareType.GPU_GENERAL: {
                "batch_size": 2,
                "quantization": "int8",
                "precision": "fp16",
                "provider": "gpu",
            },
            HardwareType.CPU_ONLY: {
                "batch_size": 1,
                "quantization": "none",
                "precision": "fp32",
                "provider": "cpu",
            },
        }
        return dict(mapping[hardware_type])

    def get_hardware_state(self) -> dict[str, Any]:
        cpu_usage = float(psutil.cpu_percent(interval=None))
        memory_available_gb = float(self._memory_info.get("available_ram_gb", 0.0))
        cores = int(psutil.cpu_count(logical=True) or 1)

        gpu_usage = 0.0
        if self._gpu_info:
            loads = [float(g.get("load", 0.0)) for g in self._gpu_info]
            if loads:
                # GPUtil load is 0..1, provider fallback is already 0.0
                gpu_usage = float(sum(loads) / len(loads) * 100.0)
        else:
            try:
                import GPUtil  # type: ignore

                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_usage = float(sum(float(gpu.load) for gpu in gpus) / len(gpus) * 100.0)
            except Exception:
                gpu_usage = 0.0

        hardware_type = self.detect_hardware_type()
        available_tiers = ["cpu"]
        if hardware_type in {HardwareType.GPU_CUDA, HardwareType.GPU_GENERAL}:
            available_tiers.append("gpu")
        if hardware_type in {HardwareType.NPU_APPLE, HardwareType.NPU_INTEL}:
            available_tiers.append("npu")

        return {
            "cpu_usage": cpu_usage,
            "memory_available_gb": memory_available_gb,
            "gpu_usage": gpu_usage,
            "available_tiers": available_tiers,
            "current_load": float(cpu_usage / max(cores, 1)),
        }


class ResourceManager:
    def __init__(self) -> None:
        self.allocations: dict[str, dict[str, Any]] = {}

    def allocate_memory(self, model_name: str, provider: str, requested_mb: int) -> dict[str, Any]:
        allocation = {
            "model_name": model_name,
            "provider": provider,
            "requested_mb": int(requested_mb),
        }
        self.allocations[model_name] = allocation
        return allocation

    def release_memory(self, model_name: str) -> bool:
        if model_name in self.allocations:
            del self.allocations[model_name]
            return True
        return False

    def check_resource_exhaustion(self) -> str | None:
        mem_percent = float(psutil.virtual_memory().percent)
        if mem_percent > 95:
            return "critical_memory_exhaustion"
        if mem_percent > 90:
            return "high_memory_pressure"

        cpu_percent = float(psutil.cpu_percent(interval=None))
        if cpu_percent > 95:
            return "cpu_exhaustion"

        return None
