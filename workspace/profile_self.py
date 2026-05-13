import psutil, time, matplotlib.pyplot as plt, os

# Get current process ID (fallback to known PID if needed)
pid = int(os.getenv('AGENT_PID', '1768'))
proc = psutil.Process(pid)

# Initialize CPU percent measurement
proc.cpu_percent(interval=None)

# Data containers
times = []
mem_rss = []  # in MB
cpu_perc = []
handles = []

duration = 60  # seconds
interval = 5   # seconds
samples = int(duration / interval) + 1

for i in range(samples):
    elapsed = i * interval
    times.append(elapsed)
    # Memory usage (RSS) in MB
    mem_rss.append(proc.memory_info().rss / (1024 * 1024))
    # CPU percent since last call
    cpu_perc.append(proc.cpu_percent(interval=None))
    # Number of handles (Windows only)
    try:
        handles.append(proc.num_handles())
    except Exception:
        handles.append(0)
    if i < samples - 1:
        time.sleep(interval)

# Plotting
plt.figure(figsize=(10, 8))

plt.subplot(3, 1, 1)
plt.plot(times, mem_rss, marker='o')
plt.title('Process RAM Usage (MB)')
plt.ylabel('MB')
plt.grid(True)

plt.subplot(3, 1, 2)
plt.plot(times, cpu_perc, color='orange', marker='o')
plt.title('Process CPU %')
plt.ylabel('%')
plt.grid(True)

plt.subplot(3, 1, 3)
plt.plot(times, handles, color='green', marker='o')
plt.title('Process Open Handles')
plt.xlabel('Time (s)')
plt.ylabel('Count')
plt.grid(True)

plt.tight_layout()
output_path = os.path.join(os.getenv('WORKSPACE_ROOT', r'C:\AgenticOs\workspace'), 'process_profile.png')
plt.savefig(output_path)
print(f'Chart saved to {output_path}')
