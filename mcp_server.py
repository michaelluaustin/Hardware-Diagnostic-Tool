import asyncio
import csv
import math
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

import psutil
from mcp.server.fastmcp import FastMCP
from pydantic import Field

DATA_DIR = Path(__file__).resolve().parent / "data"
GIB = 1024 ** 3

MIN_DURATION, MAX_DURATION = 1, 60  # seconds
MIN_INTERVAL, MAX_INTERVAL = 1, 10  # seconds

CSV_HEADER = ["Timestamp", "CPU Usage (%)", "Memory Usage (%)", "Memory Available (GiB)", "Memory Total (GiB)", "Memory Used (GiB)"]

LIMITATIONS = (
    "Measures software-visible CPU and memory utilization only (via psutil / /proc). "
    "CPU temperature, voltages, fan speeds, disk health and physical hardware condition are NOT measured. "
    "In a virtual machine, values are relative to the guest's virtual CPUs and memory."
)

mcp = FastMCP(
    "hardware-diagnostics",
    instructions="Read-only CPU and memory utilization tools for this Linux machine. " + LIMITATIONS,
)

# validates range, and raises ValueError, which FastMCP returns as an error result
def validate_range(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    if not math.isfinite(value) or not (low <= value <= high):
        raise ValueError(f"{name} must be between {low} and {high}, got {value!r}")
    return value

# validates monitor arguments
def validate_monitor_args(duration_seconds, interval_seconds, cpu_threshold, memory_threshold):
    validate_range("duration_seconds", duration_seconds, MIN_DURATION, MAX_DURATION)
    validate_range("interval_seconds", interval_seconds, MIN_INTERVAL, MAX_INTERVAL)
    validate_range("cpu_threshold", cpu_threshold, 0.0, 100.0)
    validate_range("memory_threshold", memory_threshold, 0.0, 100.0)
    if interval_seconds > duration_seconds:
        raise ValueError(f"interval_seconds ({interval_seconds}) must not exceed duration_seconds ({duration_seconds})")

# returns processor name
def processor_description():
    name = platform.processor()
    if name and name != platform.machine():
        return name
    # platform.processor() is often empty on Linux; fall back to reading /proc/cpuinfo
    try:
        with open("/proc/cpuinfo") as file:
            for line in file:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None

# returns memory info
def memory_snapshot():
    memory = psutil.virtual_memory()
    return {
        "memory_percent": memory.percent,
        "memory_available_gib": round(memory.available / GIB, 3),
        "memory_total_gib": round(memory.total / GIB, 3),
        "memory_used_gib": round(memory.used / GIB, 3),
    }


def summarize(cpu_values, memory_values, cpu_threshold, memory_threshold):
    count = len(cpu_values)
    if count == 0 or len(memory_values) != count:
        raise ValueError("summarize needs the same, non-zero number of CPU and memory samples")
    return {
        "cpu_avg_percent": round(sum(cpu_values) / count, 2),
        "cpu_peak_percent": max(cpu_values),
        "memory_avg_percent": round(sum(memory_values) / count, 2),
        "memory_peak_percent": max(memory_values),
        "cpu_threshold_violations": sum(1 for value in cpu_values if value >= cpu_threshold),
        "memory_threshold_violations": sum(1 for value in memory_values if value >= memory_threshold),
    }


def interpret(summary, sample_count, cpu_threshold, memory_threshold):
    notes = [
        f"Observed over {sample_count} sample(s): CPU averaged {summary['cpu_avg_percent']}% "
        f"(peak {summary['cpu_peak_percent']}%), memory averaged {summary['memory_avg_percent']}% "
        f"(peak {summary['memory_peak_percent']}%)."
    ]
    for label, key, threshold in (("CPU", "cpu_threshold_violations", cpu_threshold),
                                  ("Memory", "memory_threshold_violations", memory_threshold)):
        violations = summary[key]
        if violations:
            notes.append(f"{label} was at or above {threshold}% in {violations} of {sample_count} sample(s). "
                         "This shows high software load during this window; it does not indicate a hardware fault.")
        else:
            notes.append(f"{label} stayed below {threshold}% in every sample.")
    notes.append("CPU % is a system-wide average, so a single saturated core can look like a low value. "
                 "A short window may miss brief spikes or longer-term trends.")
    notes.append("Possible follow-ups: identify the top processes (e.g. with top), check per-core usage, "
                 "repeat the measurement over a longer or more representative window, and use dedicated tools "
                 "(e.g. sensors, smartctl, memtest86+, dmesg) if physical hardware health is in question.")
    return " ".join(notes)


def write_csv(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / f"monitor_{stamp}.csv"
    suffix = 1
    while path.exists():  # avoid overwriting a run started in the same second
        path = DATA_DIR / f"monitor_{stamp}_{suffix}.csv"
        suffix += 1
    with open(path, "x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    return path


@mcp.tool()
def get_system_info() -> dict:
    """Identify this machine: OS, kernel release, architecture, processor, CPU counts and total RAM."""
    return {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": processor_description(),
        "logical_cpus": psutil.cpu_count(logical=True),
        "physical_cpus": psutil.cpu_count(logical=False),  # may be null in some VMs
        "total_ram_gib": round(psutil.virtual_memory().total / GIB, 2),
        "limitations": LIMITATIONS,
    }


@mcp.tool()
async def get_current_metrics() -> dict:
    """Take one snapshot of CPU utilization (averaged over 1 second) and memory utilization."""
    psutil.cpu_percent(interval=None)  # first call only sets the baseline
    await asyncio.sleep(1)
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = memory_snapshot()
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_percent": cpu_percent,
        "memory_percent": memory["memory_percent"],
        "memory_used_gib": memory["memory_used_gib"],
        "memory_available_gib": memory["memory_available_gib"],
        "note": "CPU temperature and physical hardware health are not measured. " + LIMITATIONS,
    }


@mcp.tool()
async def monitor_resources(
    # strict=True stops the SDK from converting true/false or "10" into numbers before validation
    duration_seconds: Annotated[int, Field(strict=True)] = 10,
    interval_seconds: Annotated[int, Field(strict=True)] = 1,
    cpu_threshold: Annotated[float, Field(strict=True)] = 85.0,
    memory_threshold: Annotated[float, Field(strict=True)] = 90.0,
) -> dict:
    """Sample CPU and memory for a bounded time (1-60 s, every 1-10 s), save readings to a CSV under data/,
    and summarize averages, peaks and threshold violations (a sample counts when value >= threshold)."""
    validate_monitor_args(duration_seconds, interval_seconds, cpu_threshold, memory_threshold)

    sample_count = int(duration_seconds // interval_seconds)  # >= 1 because interval <= duration
    rows, cpu_values, memory_values = [], [], []

    start = time.monotonic()
    psutil.cpu_percent(interval=None)
    for _ in range(sample_count):
        await asyncio.sleep(interval_seconds)
        cpu_percent = psutil.cpu_percent(interval=None)  # average since the previous call
        memory = memory_snapshot()
        cpu_values.append(cpu_percent)
        memory_values.append(memory["memory_percent"])
        rows.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cpu_percent, memory["memory_percent"],
                     memory["memory_available_gib"], memory["memory_total_gib"], memory["memory_used_gib"]])
    elapsed = round(time.monotonic() - start, 2)

    summary = summarize(cpu_values, memory_values, cpu_threshold, memory_threshold)
    result = {
        "sample_count": sample_count,
        "requested_duration_seconds": duration_seconds,
        "interval_seconds": interval_seconds,
        "actual_duration_seconds": elapsed,
        "cpu_threshold": cpu_threshold,
        "memory_threshold": memory_threshold,
        **summary,
        "csv_path": None,
        "interpretation": interpret(summary, sample_count, cpu_threshold, memory_threshold),
        "limitations": LIMITATIONS,
    }
    try:
        result["csv_path"] = str(write_csv(rows))
    except OSError as error:
        result["csv_error"] = f"Could not save CSV: {error}"
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")