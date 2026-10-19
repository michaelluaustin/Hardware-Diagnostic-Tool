# Linux System Performance & Diagnostics Tool

A small Python toolkit that monitors CPU and memory utilization on Linux, logs timestamped measurements to CSV, and analyzes and plots the results.

## Overview

The tool samples system-wide CPU and memory usage once per second through [psutil](https://github.com/giampaolo/psutil), which reads the same kernel interfaces (`/proc`) used by tools like `top` and `free`. Measurements are written to a CSV file, summarized with basic statistics, and plotted over time.

I built it to learn how the operating system exposes hardware resource usage to software, and how to collect, validate and interpret performance measurements. It measures **software-visible utilization only**: it does not perform hardware, thermal or physical diagnostics.

## Features

- **`cpu_monitor.py`**
  - Prints a system snapshot: logical CPU count, available memory, OS, kernel release and Python version.
  - Logs CPU %, memory %, and available/total/used memory (GiB) to `system_metrics.csv` every second.
  - Warns in the terminal when CPU or memory usage exceeds a configurable threshold.
  - Validates threshold arguments: rejects non-numeric values, values outside 0–100, `nan` and `inf`.
  - Stops cleanly with Ctrl-C.
- **`analyze_metrics.py`**: reports average and maximum CPU usage, average and maximum memory usage, and minimum available memory.
- **`plot_metrics.py`**: plots CPU and memory usage over time to `metrics.png`. Works without a display (headless).

Both the analyzer and the plotter exit with an error message and exit code 1 if the CSV is missing.

## Requirements

- Linux (developed on Ubuntu 24.04.5 LTS)
- Python 3.12
- psutil 7.2.2
- matplotlib 3.11.2

## Setup

```bash
git clone https://github.com/michaelluaustin/Hardware-Diagnostic-Tool.git
cd Hardware-Diagnostic-Tool
python3 -m venv .venv
source .venv/bin/activate
pip install psutil matplotlib
```

## Usage

Run all commands from the project folder.

```bash
# Start monitoring (default thresholds: CPU 60%, memory 70%); stop with Ctrl-C
python cpu_monitor.py

# Custom warning thresholds
python cpu_monitor.py --cpu-threshold 80 --memory-threshold 90

# Summarize the recorded run
python analyze_metrics.py

# Plot the recorded run to metrics.png
python plot_metrics.py
```

## Example Results

Test machine: Intel Core i5-14600 (14 cores: 6 performance cores with Hyper-Threading and 8 efficiency cores, for 20 logical CPUs), 31.04 GiB RAM.

I compared an idle run with a run under a controlled CPU workload. While the monitor was running, I started this single-threaded Python busy loop in a second terminal. It increments a counter as fast as possible for 20 seconds and then exits on its own:

```python
import time
end = time.time() + 20
x = 0
while time.time() < end:
    x += 1
print("Workload finished")
```

| Metric | Idle (18 s) | Workload (30 s, ~20 s under load) |
|---|---|---|
| Average CPU usage | 0.17% | 3.50% |
| Maximum CPU usage | 0.30% | 5.40% |
| Memory usage | 17.1% | 17.0% |
| Minimum memory available | 25.73 GiB | 25.75 GiB |

![CPU and memory usage over time](metrics.png)

**Observations**

- During the workload, CPU usage held steady at about 5.1%. That is what one fully busy logical CPU looks like on this machine: 100% ÷ 20 logical CPUs = 5%. System-wide CPU percentage can therefore hide a single saturated core.
- Memory usage barely changed between runs.
- `Memory Used + Memory Available` does not add up to `Memory Total`. Linux counts reclaimable page cache as available but not as used.

## Testing

The tool was manually tested on Ubuntu 24.04.5 LTS using Python 3.12.

| Test | Expected result | Outcome |
|---|---|---|
| Valid CPU and memory thresholds | Accepted and monitoring starts | Passed |
| Threshold above 100 or below 0 | Rejected with an argument error | Passed |
| Non-numeric threshold input | Rejected with an argument error | Passed |
| `nan`, `inf`, or `-inf` threshold | Rejected with an argument error | Passed (`nan` was initially accepted; fixed) |
| CSV analysis with valid data | Correct averages, maximums, and minimum available memory are reported | Passed |
| Empty CSV containing only headers | Informative message is printed without a calculation error | Passed |
| Analysis or plotting with no CSV file present | Error message is printed and the script exits with code 1 | Passed |
| Monitoring interrupted with Ctrl+C | Monitoring stops gracefully and recorded data remains saved | Passed |
| Plot generation from valid CSV data | CPU and memory usage graph is saved as a PNG | Passed |
| Controlled CPU workload compared with idle run | Average and maximum CPU usage increase during the workload | Observed as expected |

Testing was performed manually; no automated test suite has been added. Results may vary depending on system activity and whether the environment is virtualized.

## Limitations

- **System-wide averages only.** A single saturated core shows up as about 5% CPU, so the default 60% threshold would not flag it. Per-core monitoring would be needed for that.
- **1-second sampling.** Each row is a 1-second average, so shorter spikes are smoothed out. Timestamps mark the start of each sample window, have 1-second resolution, and drift slightly over long runs.
- **Virtualized environments.** In a VM, CPU usage is relative to the guest's virtual CPUs, and time taken by the host is not visible.
- **Data is saved reliably only on Ctrl-C.** Writes are buffered, so killing the process (for example with `kill`) can leave an empty or incomplete CSV.
- **The analyzer assumes a well-formed CSV.** Blank or truncated rows cause it to crash.
- **Each run overwrites** `system_metrics.csv` and `metrics.png`.
- **Warnings go to the terminal only.** They print every second while over the threshold and are not recorded in the CSV.
- **The monitor's own overhead** is included in the measurements, although it is very small.
- **Files are read and written in the current working directory**, so the scripts should be run from the project folder.
