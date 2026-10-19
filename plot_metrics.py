import csv
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

INPUT_FILE = "system_metrics.csv"
OUTPUT_FILE = "metrics.png"

# Exit with an error code if there is no data to plot
if not os.path.exists(INPUT_FILE):
    print(f"Error: {INPUT_FILE} not found. Run cpu_monitor.py first to get data.")
    sys.exit(1)

with open(INPUT_FILE, 'r') as file:
    reader = csv.DictReader(file)
    timestamps = []
    cpu_usages = []
    memory_usages = []
    for row in reader:
        timestamps.append(datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")) # Convert to datetime objects
        cpu_usages.append(float(row["CPU Usage (%)"]))
        memory_usages.append(float(row["Memory Usage (%)"]))
    plt.plot(timestamps, cpu_usages, label="CPU Usage over time")
    plt.plot(timestamps, memory_usages, label="Memory Usage over time")
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=6)) # 4-6 time label ticks
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S")) # Format as H:M:S
    plt.xlabel("Time")
    plt.ylabel("CPU and Memory Usage (%)")
    plt.title("CPU and Memory Usage over time")
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_FILE)
    print(f"CPU and Memory plot saved to {OUTPUT_FILE}")