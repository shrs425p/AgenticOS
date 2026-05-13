import os
import sys
import time

# Force UTF-8 encoding for Windows console to support emojis (⚠, etc.)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add the parent directory to sys.path so we can import core
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from core.runtime import Agent
from core.runtime_config import load_config
from core.runtime_ui import print_success, print_error, print_info

class Logger:
    """Tee stdout/stderr to a file while still printing to terminal."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def isatty(self):
        return self.terminal.isatty()

    @property
    def encoding(self):
        return self.terminal.encoding

def main():
    # Redirect all terminal output to a log file
    sys.stdout = Logger("evaluation_output.txt")
    sys.stderr = sys.stdout
    
    print_info("Initializing AgenticOS Evaluation Harness...")
    
    # Load config and enforce autopilot
    cfg = load_config()
    if "agent" not in cfg:
        cfg["agent"] = {}
    if "autonomy" not in cfg:
        cfg["autonomy"] = {}
        
    cfg["agent"]["auto_confirm"] = True
    cfg["autonomy"]["autopilot"] = True
    
    agent = Agent(cfg)
    
    # Read the first 3 tasks from task.md
    task_file = os.path.join(base_dir, "task.md")
    tasks = []
    with open(task_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith(("#", "🌐", "🖥️", "🔁", "🤖")):
                tasks.append(line)
                
    print_info(f"Loaded {len(tasks)} tasks for evaluation.")
    
    results = {}
    total_tasks = len(tasks)
    
    for i, task_desc in enumerate(tasks, 1):
        print_info(f"\n{'='*50}\nStarting Evaluation Task {i}/{total_tasks}\n{'='*50}")
        print_info(f"Task: {task_desc}")
        
        # Give the agent a clean session memory for each task
        agent.memory.clear()
        
        try:
            start_time = time.time()
            agent.run(task_desc)
            duration = time.time() - start_time
            print_success(f"Task {i} completed in {duration:.1f} seconds.")
            results[f"Task {i}"] = "Completed"
        except Exception as e:
            print_error(f"Task {i} failed: {e}")
            results[f"Task {i}"] = f"Failed: {e}"
            
        if i < total_tasks:
            print_info("Sleeping for 15 seconds to respect API rate limits...")
            time.sleep(15)
            
    print_info("\n" + "="*50)
    print_info("EVALUATION SUMMARY")
    print_info("="*50)
    for task_name, status in results.items():
        if "Completed" in status:
            print_success(f"{task_name}: {status}")
        else:
            print_error(f"{task_name}: {status}")

if __name__ == "__main__":
    main()
