import csv
import os
import sys

INPUT_FILE = "system_metrics.csv"

# Exit with an error code if there is no data to analyze
if not os.path.exists(INPUT_FILE):
    print(f"Error: {INPUT_FILE} not found. Run cpu_monitor.py first to get data.")
    sys.exit(1)

with open(INPUT_FILE, 'r') as file:
    reader = csv.DictReader(file)
    
    total_cpu_usage = 0
    max_cpu_usage = 0
    total_memory_usage = 0
    max_memory_usage = 0
    min_memory_available = float('inf')
    
    rowCount = 0
    for row in reader:
        total_cpu_usage += float(row["CPU Usage (%)"])
        max_cpu_usage = max(max_cpu_usage, float(row["CPU Usage (%)"]))
        total_memory_usage += float(row["Memory Usage (%)"])
        max_memory_usage = max(max_memory_usage, float(row["Memory Usage (%)"]))
        min_memory_available = min(min_memory_available, float(row["Memory Available (GiB)"]))
        rowCount += 1
    if rowCount == 0:
        print("No data available to analyze.")
    else:
        print(f"Average CPU Usage: {total_cpu_usage / rowCount:.2f}%")
        print(f"Maximum CPU Usage: {max_cpu_usage:.2f}%")
        print(f"Average Memory Usage: {total_memory_usage / rowCount:.2f}%")
        print(f"Maximum Memory Usage: {max_memory_usage:.2f}%")
        print(f"Minimum Memory Available: {min_memory_available:.2f} (GiB)")
    