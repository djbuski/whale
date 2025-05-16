import subprocess
import time
import sys

def run_bot():
    """Runs the Solana tracker bot and restarts it if it crashes."""
    script_to_run = "/home/ubuntu/solana_tracker_core.py"
    restart_delay_seconds = 30 # Wait 30 seconds before restarting

    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting {script_to_run}...")
        process = None # Initialize process to None
        try:
            # Start the bot script as a subprocess
            process = subprocess.Popen([sys.executable, script_to_run],
                                     stdout=sys.stdout, 
                                     stderr=sys.stderr)
            # Wait for the process to complete
            process.wait()
            
            # If the process completed, check its return code
            # A non-zero return code might indicate an error, but for simplicity,
            # we'll restart even on a zero return code if it wasn't a KeyboardInterrupt.
            # The main bot script should ideally handle its own graceful shutdown via KeyboardInterrupt.
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {script_to_run} exited with code {process.returncode}.")

        except KeyboardInterrupt:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Wrapper script received KeyboardInterrupt. Stopping...")
            if process and process.poll() is None: # Check if process is still running
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Terminating the bot script...")
                process.terminate() # Try to terminate gracefully
                try:
                    process.wait(timeout=10) # Wait for termination
                except subprocess.TimeoutExpired:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Bot script did not terminate in time, killing...")
                    process.kill() # Force kill if terminate doesn't work
            break # Exit the while loop
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] An error occurred in the wrapper script: {e}")
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Restarting {script_to_run} in {restart_delay_seconds} seconds...")
        time.sleep(restart_delay_seconds)

if __name__ == "__main__":
    run_bot()

