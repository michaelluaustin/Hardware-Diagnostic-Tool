---
name: hardware-diagnostics
description: Analyze CPU and memory utilization using the Hardware Diagnostics MCP tools.
---

# Hardware Diagnostics (CPU and memory utilization)

Use the `hardware-diagnostics` MCP server tools to investigate CPU and memory utilization on this Linux machine. These tools measure **software-visible utilization only**. They do not measure temperature, voltage, fan speed, electrical signals, disk health, or the physical condition of any component.

## Workflow

1. **Identify the system first.** Call `get_system_info` before diagnosing anything. Note the OS, kernel release, architecture, processor, logical/physical CPU counts and total RAM. If the processor name or a missing physical CPU count suggests a virtual machine, say so, because VM utilization is relative to the guest's virtual resources and host contention is not visible.

2. **Collect a baseline.** Call `get_current_metrics` for a single snapshot (CPU averaged over 1 second, plus memory). One snapshot is a point-in-time reading, not a trend.

3. **Monitor only when needed, and keep it bounded.** If a snapshot is not enough (e.g. the user reports intermittent slowness), call `monitor_resources`.
   - Start short: 10–30 seconds at a 1–2 second interval. The tool accepts at most 60 seconds and intervals of 1–10 seconds.
   - Pick thresholds that fit the question; the defaults are 85% CPU and 90% memory.
   - If the symptom is intermittent or workload-dependent, ask the user to reproduce it during the monitoring window.
   - Report the CSV path the tool returns (saved under `data/`).

4. **Interpret accurately.**
   - Compare **average vs. peak**: a high peak with a low average suggests brief spikes; a high average suggests sustained load.
   - Report threshold violations as "k of N samples at or above X%", not as a pass/fail verdict.
   - CPU % is a system-wide average across all logical CPUs. One fully busy core shows up as roughly 100% ÷ logical CPU count, so a low system-wide value does not rule out a single saturated core.
   - Memory "used" plus "available" does not equal "total" on Linux, because reclaimable page cache counts as available.
   - A short window can miss brief spikes and cannot show long-term trends.

5. **Report in four sections:**
   - **Observed:** the measured numbers only, with sample count and duration.
   - **Interpretation / hypotheses:** possible explanations, each clearly labeled as a hypothesis, not a finding.
   - **Not measured:** state the tool limitations explicitly (see below).
   - **Recommended follow-ups:** what would confirm or rule out each hypothesis.

## Rules

- **Never infer physical hardware failure from utilization metrics alone.** High CPU or memory usage indicates software load, not a faulty component.
- Do not claim to have measured temperatures, voltages, electrical signals, disk health, or physical hardware condition.
- Distinguish what was observed from what is suspected. Do not present a hypothesis as a conclusion.
- When the evidence is insufficient, say so and recommend follow-up tests instead of guessing, for example:
  - identify the top processes (`top`, `ps`) and check per-core usage (`mpstat -P ALL`)
  - repeat monitoring over a longer or more representative window, or while reproducing the problem
  - for suspected physical issues, dedicated tools such as `sensors` (temperatures), `smartctl` (disk health), `memtest86+` (RAM), `dmesg` / `journalctl -k` (kernel hardware errors), or vendor diagnostics
- Suggest these commands for the user to run; do not run shell commands as a substitute for the MCP tools unless the user asks.

## Limitations to state in every report

- Software-visible CPU and memory utilization only, sampled via psutil (`/proc`).
- No temperature, voltage, fan, power, electrical, disk-health, or physical-condition measurements.
- System-wide CPU averages can hide per-core saturation; sampling intervals smooth out short spikes.
- In a virtual machine, values are relative to the guest and do not show host contention.
