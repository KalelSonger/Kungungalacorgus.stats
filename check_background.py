"""Script to check and terminate background Flask/ngrok processes"""
import psutil
import os

def find_background_processes():
    """Find all Flask and ngrok processes"""
    current_pid = os.getpid()
    parent_pid = os.getppid()  # Get parent process ID (the menu)
    processes = {
        'flask': [],
        'ngrok': []
    }
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                proc_name = proc.info['name']
                if proc_name and 'python' in proc_name.lower():
                    cmdline = proc.info['cmdline']
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    # Only detect Flask processes with --flask-only flag
                    # Exclude current process, parent process (menu), and menu processes
                    if cmdline and 'main.py' in cmdline_str and '--flask-only' in cmdline_str:
                        if proc.info['pid'] != current_pid and proc.info['pid'] != parent_pid:
                            processes['flask'].append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline_str[:80] if cmdline_str else 'N/A'
                            })
                elif proc_name and 'ngrok' in proc_name.lower():
                    processes['ngrok'].append({
                        'pid': proc.info['pid'],
                        'cmdline': ' '.join(proc.info['cmdline'])[:80] if proc.info['cmdline'] else 'N/A'
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        print(f"Error scanning processes: {e}")
    
    return processes

def terminate_processes(process_list):
    """Terminate a list of processes"""
    terminated = []
    failed = []
    
    for proc_info in process_list:
        try:
            proc = psutil.Process(proc_info['pid'])
            proc.terminate()
            proc.wait(timeout=3)
            terminated.append(proc_info['pid'])
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                terminated.append(proc_info['pid'])
            except Exception as e:
                failed.append((proc_info['pid'], str(e)))
        except Exception as e:
            failed.append((proc_info['pid'], str(e)))
    
    return terminated, failed

def main():
    """Main function to check and optionally terminate background processes"""
    print("\n" + "="*60)
    print("Background Process Check")
    print("="*60)
    
    processes = find_background_processes()
    
    total_found = len(processes['flask']) + len(processes['ngrok'])
    
    if total_found == 0:
        print("\n✓ No background Flask or ngrok processes found.")
        return
    
    print(f"\n⚠️  Found {total_found} background process(es):\n")
    
    if processes['flask']:
        print(f"Flask/Python processes ({len(processes['flask'])}):")
        for proc in processes['flask']:
            print(f"  - PID: {proc['pid']}")
            print(f"    Command: {proc['cmdline'][:80]}...")
    
    if processes['ngrok']:
        print(f"\nNgrok processes ({len(processes['ngrok'])}):")
        for proc in processes['ngrok']:
            print(f"  - PID: {proc['pid']}")
            print(f"    Command: {proc['cmdline'][:80]}...")
    
    print("\n" + "-"*60)
    response = input("Do you want to terminate these processes? (y/n): ").strip().lower()
    
    if response == 'y':
        all_processes = processes['flask'] + processes['ngrok']
        print("\nTerminating processes...")
        terminated, failed = terminate_processes(all_processes)
        
        if terminated:
            print(f"✓ Successfully terminated {len(terminated)} process(es):")
            for pid in terminated:
                print(f"  - PID: {pid}")
        
        if failed:
            print(f"\n✗ Failed to terminate {len(failed)} process(es):")
            for pid, error in failed:
                print(f"  - PID: {pid} - {error}")
    else:
        print("\n✓ No processes terminated.")

if __name__ == '__main__':
    main()
