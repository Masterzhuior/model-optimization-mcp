"""GPU discovery helpers.

The adapter prefers ``nvidia-smi`` because it is available on most GPU servers.
If it is absent, the service layer can fall back to deterministic simulated GPUs
for local demos and CI.
"""

from __future__ import annotations

import csv
import subprocess
from io import StringIO
from typing import Any


def query_nvidia_smi() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,uuid,name,memory.total,memory.used,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    gpus: list[dict[str, Any]] = []
    reader = csv.reader(StringIO(completed.stdout))
    for row in reader:
        if len(row) < 7:
            continue
        index, uuid, name, memory_total, memory_used, utilization, temperature = [
            column.strip() for column in row[:7]
        ]
        gpus.append(
            {
                "gpu_id": int(index),
                "uuid": uuid,
                "name": name,
                "memory_total_gb": round(float(memory_total) / 1024, 2),
                "memory_used_gb": round(float(memory_used) / 1024, 2),
                "utilization": round(float(utilization) / 100, 3),
                "temperature": int(float(temperature)),
                "source": "nvidia-smi",
            }
        )
    return gpus


def query_gpu_processes() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-compute-apps=pid,gpu_uuid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    processes: list[dict[str, Any]] = []
    reader = csv.reader(StringIO(completed.stdout))
    for row in reader:
        if len(row) < 4:
            continue
        pid, gpu_uuid, process_name, used_memory = [column.strip() for column in row[:4]]
        processes.append(
            {
                "pid": int(pid),
                "gpu_uuid": gpu_uuid,
                "process_name": process_name,
                "used_memory_gb": round(float(used_memory) / 1024, 2),
                "source": "nvidia-smi",
            }
        )
    return processes

