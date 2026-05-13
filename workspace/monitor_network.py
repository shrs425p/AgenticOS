import psutil, time, datetime, collections, os
import matplotlib.pyplot as plt

# Configuration
INTERVAL = 5               # seconds between measurements
DURATION = 10            # total monitoring time in seconds (2 minutes)
OUTPUT_IMAGE = 'network_usage.png'
OUTPUT_REPORT = 'network_report.md'

# Data containers
timestamps = []
bytes_sent = []
bytes_recv = []

start_time = time.time()
while time.time() - start_time < DURATION:
    now = datetime.datetime.now()
    counters = psutil.net_io_counters()
    timestamps.append(now)
    bytes_sent.append(counters.bytes_sent)
    bytes_recv.append(counters.bytes_recv)
    time.sleep(INTERVAL)

# Plot cumulative bytes sent/received over time
plt.figure(figsize=(10, 6))
plt.plot(timestamps, bytes_sent, label='Bytes Sent')
plt.plot(timestamps, bytes_recv, label='Bytes Received')
plt.xlabel('Time')
plt.ylabel('Cumulative Bytes')
plt.title('Network Bandwidth Usage (2 minutes)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(OUTPUT_IMAGE)
plt.close()

# Determine the process with the most active network connections (as a proxy for usage)
conn_counts = collections.Counter()
for conn in psutil.net_connections(kind='inet'):
    if conn.pid is not None:
        conn_counts[conn.pid] += 1

if conn_counts:
    top_pid, top_conn_num = conn_counts.most_common(1)[0]
    try:
        top_proc = psutil.Process(top_pid)
        top_name = top_proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        top_name = 'N/A'
else:
    top_pid = top_conn_num = top_name = 'N/A'

# Total data transferred
total_sent = bytes_sent[-1] - bytes_sent[0]
total_recv = bytes_recv[-1] - bytes_recv[0]

# Write markdown report
report_lines = [
    f"# Network Bandwidth Report",
    f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "",
    f"**Total Sent:** {total_sent:,} bytes",
    f"**Total Received:** {total_recv:,} bytes",
    "",
    f"**Top Process by Connection Count:**",
    f"- PID: {top_pid}",
    f"- Name: {top_name}",
    f"- Active Connections: {top_conn_num}",
    "",
    f"![Network Usage]({OUTPUT_IMAGE})",
]

with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print('Monitoring complete. Files generated:')
print(' -', OUTPUT_IMAGE)
print(' -', OUTPUT_REPORT)
