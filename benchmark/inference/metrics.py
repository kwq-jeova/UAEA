from __future__ import annotations

import subprocess


class NvidiaSmiMetricsCollector:
    """Best-effort point-in-time NVIDIA metrics for inference comparisons."""

    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index

    def sample(self) -> dict[str, float | None]:
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={self.device_index}",
                    "--query-gpu=utilization.gpu,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            values = [value.strip() for value in completed.stdout.strip().split(",")]
            if len(values) < 2:
                raise ValueError("nvidia-smi returned incomplete metrics")
            return {
                "sm_utilization_percent": float(values[0]),
                "vram_used_mb": float(values[1]),
                "kv_cache_used_mb": None,
            }
        except (OSError, subprocess.SubprocessError, ValueError):
            return {
                "sm_utilization_percent": None,
                "vram_used_mb": None,
                "kv_cache_used_mb": None,
            }
