import psutil
import platform
import time
import csv
import argparse
from datetime import datetime

OUTPUT_FILE = "system_metrics.csv"
TIME_INTERVAL = 1.0 # seconds

# Check if threshold is valid
def validate_threshold(value):
    try:
        value = float(value)
    except:
        raise argparse.ArgumentTypeError("Value has to be a number 0-100.") 
    if value >= 0.0 and value <= 100.0:
        return value
    raise argparse.ArgumentTypeError("Value has to be a number 0-100.")

def parse_args():
    parser = argparse.ArgumentParser(description="Monitor CPU and Memory Usage")
    parser.add_argument(
        "--cpu-threshold", 
        type=validate_threshold, 
        default=60.0, 
        help="CPU Usage warning threshold (%%)"
    )
    parser.add_argument(
        "--memory-threshold", 
        type=validate_threshold,
        default=70.0,
        help="Memory Usage warning threshold (%%)"
    )
    return parser.parse_args()

# Insight into system information
def system_info():
    cpu_count = psutil.cpu_count()
    available_vm = round(psutil.virtual_memory().available / 1024 ** 3, 2) # convert to GiB
    os = platform.system()
    release = platform.release()
    python_version = platform.python_version()
    return {
        "CPU Count": cpu_count,
        "Available Virtual Memory": str(available_vm) + " GiB",
        "Operating System": os,
        "Release": release,
        "Python Version": python_version
    }

def main():
    args = parse_args()
    system = system_info()
    print("------------------------------------------")
    print("System Information:")
    for key, value in system.items():
        print(f"{key}: {value}")
    print("------------------------------------------")
    print("Diagnostic running. Ctrl-C to exit")
    print("------------------------------------------")
    with open(OUTPUT_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "CPU Usage (%)", "Memory Usage (%)", "Memory Available (GiB)", "Memory Total (GiB)", "Memory Used (GiB)"]) 
        try:
            while(True):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cpu_percent = psutil.cpu_percent(TIME_INTERVAL)
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_available_gib = memory.available / (1024 ** 3)  # Convert bytes to GiB
                memory_total_gib = memory.total / (1024 ** 3)
                memory_used = memory.used / (1024 ** 3)
                writer.writerow([timestamp, cpu_percent, memory_percent, memory_available_gib, memory_total_gib, memory_used])
                # CPU Usage threshold warning
                if cpu_percent > args.cpu_threshold:
                    print(f"Warning: CPU Usage is at {cpu_percent}% (Threshold: {args.cpu_threshold}%)")
                # Memory Usage threshold warning
                if memory_percent > args.memory_threshold:
                    print(f"Warning: Memory Usage is at {memory_percent}% (Threshold: {args.memory_threshold}%)")
        except KeyboardInterrupt:
            # Clean exit with Ctrl-C
            print("\nMonitoring Stopped")
            print("Results saved in system_metrics.csv")

if __name__ == "__main__":
    main()