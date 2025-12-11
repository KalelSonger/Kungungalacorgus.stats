"""Console menu for Kungungalacorgus.stats"""
import os
import sys
import time
import subprocess
import socket
import psutil

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def check_port_in_use(port):
    """Check if a port is in use by trying to connect to it"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)  # 1 second timeout
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0  # 0 means connection successful, port is in use
    except Exception:
        sock.close()
        return False

def check_if_running():
    """Check if Flask and ngrok are running with correct versions"""
    flask_running = check_port_in_use(5000)
    ngrok_running = False
    
    # Check if ngrok is running
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'ngrok' in proc.info['name'].lower():
                ngrok_running = True
                break
    except:
        pass
    
    return flask_running, ngrok_running

def start_application():
    """Start Flask and ngrok"""
    clear_screen()
    print("\n" + "="*60)
    print("Starting Kungungalacorgus.stats")
    print("="*60 + "\n")
    
    # Check if already running
    flask_running, ngrok_running = check_if_running()
    
    if flask_running:
        print("✓ Application is already running and idling!")
        print("  - Flask: Running on port 5000")
        if ngrok_running:
            print("  - Ngrok: Running")
        print("\n  The app is ready to accept requests.")
        print("  You can continue using the menu for other operations.")
        input("\nPress Enter to return to menu...")
        return
    
    # Start the application
    print("Starting Flask server...")
    try:
        # Start main.py with --flask-only flag
        # The new console will show output directly
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                ['.venv\\Scripts\\python.exe', 'main.py', '--flask-only'],
                creationflags=subprocess.CREATE_NEW_CONSOLE
                # Output now goes to the console window (not hidden in a log file)
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                ['.venv/bin/python', 'main.py', '--flask-only']
            )
        
        print("✓ Starting application...")
        print("\n  Waiting for services to start...")
        
        # Wait for Flask to start
        max_wait = 10
        flask_started = False
        for i in range(max_wait):
            time.sleep(1)
            if check_port_in_use(5000):
                print("  ✓ Flask started on port 5000")
                flask_started = True
                break
            # Check if process crashed
            if process.poll() is not None:
                print(f"\n\n✗ Flask process terminated unexpectedly!")
                print("\n  Check the Flask console window for error details.")
                break
            sys.stdout.write(f"\r  Waiting... {i+1}/{max_wait}s")
            sys.stdout.flush()
        
        print("\n")
        
        # Check final status
        flask_running, ngrok_running = check_if_running()
        
        if flask_running:
            print("✓ Application started successfully and is now idling!")
            print("\n  Access your app at:")
            print("    - Local: http://localhost:5000")
            print("    - Ngrok: https://easily-crankier-coleman.ngrok-free.dev")
            print("\n  A separate console window is showing Flask server logs.")
            print("  You can use this menu for other operations.")
        else:
            if not flask_started:
                print("✗ Failed to start Flask. Check the Flask console window for errors.")
        
    except Exception as e:
        print(f"\n✗ Error starting application: {e}")
        print("\n  Check the Flask console window for detailed error messages.")
    
    input("\nPress Enter to return to menu...")

def check_background():
    """Check for background processes"""
    clear_screen()
    print("\n" + "="*60)
    print("Checking Background Processes")
    print("="*60 + "\n")
    
    # Check if app is currently running
    flask_running, ngrok_running = check_if_running()
    
    if flask_running:
        print("ℹ️  Application is currently running and idling.")
        print("   Background check is not recommended while app is active.")
        print("\n   If you want to check for issues, use option 3 to stop")
        print("   the app first, then run this check.")
        input("\nPress Enter to return to menu...")
        return
    
    try:
        # Run the check_background.py script
        if os.name == 'nt':  # Windows
            subprocess.run(['.venv\\Scripts\\python.exe', 'check_background.py'])
        else:  # Linux/Mac
            subprocess.run(['.venv/bin/python', 'check_background.py'])
    except Exception as e:
        print(f"Error running background check: {e}")
    
    input("\nPress Enter to return to menu...")

def stop_application():
    """Stop Flask and ngrok"""
    while True:  # Loop to allow retrying
        clear_screen()
        print("\n" + "="*60)
        print("Stopping Application")
        print("="*60 + "\n")
        
        flask_running, ngrok_running = check_if_running()
        
        if not flask_running and not ngrok_running:
            print("✓ No application processes are currently running.")
            input("\nPress Enter to return to menu...")
            return
        
        print("Terminating processes...\n")
        
        terminated = []
        failed = []
        current_pid = os.getpid()  # Don't terminate the menu itself
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name']
                    if proc_name:
                        # Check for Flask (Python running main.py with --flask-only flag)
                        if 'python' in proc_name.lower():
                            cmdline = proc.info['cmdline']
                            cmdline_str = ' '.join(cmdline) if cmdline else ''
                            # Only terminate Flask processes with --flask-only flag, not the menu
                            if cmdline and 'main.py' in cmdline_str and '--flask-only' in cmdline_str:
                                if proc.info['pid'] != current_pid:
                                    proc.terminate()
                                    proc.wait(timeout=3)
                                    terminated.append(('Flask', proc.info['pid']))
                        
                        # Check for ngrok
                        elif 'ngrok' in proc_name.lower():
                            proc.terminate()
                            proc.wait(timeout=3)
                            terminated.append(('Ngrok', proc.info['pid']))
                
                except psutil.TimeoutExpired:
                    try:
                        proc.kill()
                        terminated.append((proc_name, proc.info['pid']))
                    except Exception as e:
                        failed.append((proc_name, proc.info['pid'], str(e)))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"Error during termination: {e}")
        
        if terminated:
            print(f"✓ Successfully stopped {len(terminated)} process(es):")
            for name, pid in terminated:
                print(f"  - {name} (PID: {pid})")
        
        if failed:
            print(f"\n✗ Failed to stop {len(failed)} process(es):")
            for name, pid, error in failed:
                print(f"  - {name} (PID: {pid}) - {error}")
        
        if not terminated and not failed:
            print("✓ Application stopped successfully.")
            input("\nPress Enter to return to menu...")
            return
        
        # If there were failures, check if processes still exist
        if failed:
            print("\n" + "-"*60)
            print("Checking for remaining processes...\n")
            time.sleep(1)  # Brief pause before rechecking
            
            flask_running, ngrok_running = check_if_running()
            
            if flask_running or ngrok_running:
                print("⚠️  Some processes are still running:")
                if flask_running:
                    print("   - Flask is still active")
                if ngrok_running:
                    print("   - Ngrok is still active")
                
                print("\n" + "-"*60)
                retry = input("\nDo you want to try terminating again? (yes/no): ").strip().lower()
                
                if retry == 'yes':
                    continue  # Loop back to try again
                else:
                    print("\n✓ Returning to menu. Processes are still running.")
                    input("\nPress Enter to return to menu...")
                    return
            else:
                print("✓ All processes have been stopped despite errors.")
                input("\nPress Enter to return to menu...")
                return
        else:
            # All successful, return to menu
            input("\nPress Enter to return to menu...")
            return

def clear_database_menu():
    """Clear the database"""
    clear_screen()
    print("\n" + "="*60)
    print("Clear Database")
    print("="*60 + "\n")
    
    print("⚠️  WARNING: This will delete ALL your data!")
    print("   - All songs will be removed")
    print("   - All artists will be removed")
    print("   - All albums will be removed")
    print("   - All relationships will be removed")
    
    print("\n" + "-"*60)
    response = input("Are you sure you want to clear the database? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print("\nClearing database...")
        try:
            from database import clear_all_data
            clear_all_data()
            print("\n✓ Database cleared successfully!")
        except Exception as e:
            print(f"\n✗ Error clearing database: {e}")
    else:
        print("\n✓ Database clear cancelled.")
    
    input("\nPress Enter to return to menu...")

def check_database_menu():
    """Check database entry counts"""
    clear_screen()
    print("\n" + "="*60)
    print("Database Statistics")
    print("="*60 + "\n")
    
    print("Fetching database counts...\n")
    
    try:
        # Import main module to access get_database_counts
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from main import get_database_counts
        
        counts = get_database_counts()
        
        if counts:
            print("Current Database Entries:")
            print("-"*60)
            print(f"  🎵 Songs:       {counts['songs']:,}")
            print(f"  🎤 Artists:     {counts['artists']:,}")
            print(f"  💿 Albums:      {counts['albums']:,}")
            print(f"  ▶️  Total Plays: {counts['total_plays']:,}")
            print("-"*60)
        else:
            print("✗ Failed to retrieve database counts")
            print("  Make sure the database is properly configured")
    
    except Exception as e:
        print(f"✗ Error checking database: {e}")
    
    input("\nPress Enter to return to menu...")

def populate_database_menu():
    """Load all recent history from Spotify"""
    clear_screen()
    print("\n" + "="*60)
    print("Load Recent History")
    print("="*60 + "\n")
    
    print("📈 This will load all available tracks from your Spotify recent history")
    print("   • Fetches up to 50 most recent tracks")
    print("   • Skips tracks already in database")
    print("   • Shows if history is already synced")
    print("\n💡 Note: Background sync runs every 2 minutes to add new plays automatically")
    
    print("\n" + "-"*60)
    
    # Check if app is running
    flask_running, _ = check_if_running()
    if not flask_running:
        print("⚠️  Flask is not running. Starting it may be needed for auth.")
        response = input("\nDo you want to continue anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n✓ Operation cancelled.")
            input("\nPress Enter to return to menu...")
            return
    
    try:
        confirm = input("\nLoad recent history now? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("\n✓ Operation cancelled.")
            input("\nPress Enter to return to menu...")
            return
        
        # Import and call populate function
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from main import populate_database_bulk
        
        result = populate_database_bulk()
        
        # Results are already printed by the function
        if not result.get('success') and result.get('error'):
            print(f"\n✗ Failed: {result.get('error')}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    input("\nPress Enter to return to menu...")

def help_menu():
    """Display help information for all menu options"""
    clear_screen()
    print("\n" + "="*60)
    print("     Menu Options Help")
    print("="*60 + "\n")
    
    print("1. Start Application")
    print("   Launches the Flask web server and ngrok tunnel.")
    print("   The app runs in the background while you use the menu.")
    print("   Access at: http://localhost:5000 or your ngrok URL.")
    print()
    
    print("2. Stop Application")
    print("   Terminates all Flask and ngrok processes.")
    print("   Use this to cleanly shut down the application.")
    print()
    
    print("3. Check Background Processes")
    print("   Scans for any Python/Flask or ngrok processes running.")
    print("   Useful for troubleshooting if app won't start.")
    print("   Note: Not recommended while app is running.")
    print()
    
    print("4. Check Database")
    print("   Displays current database statistics:")
    print("   - Number of songs, artists, and albums")
    print("   - Total play count across all tracks")
    print()
    
    print("5. Populate Database")
    print("   Bulk loads tracks from your Spotify listening history.")
    print("   - Loads in batches of 50 (Spotify API limit)")
    print("   - Handles rate limiting with 2-second pauses")
    print("   - You specify how many tracks to load")
    print("   - Limited by Spotify's recently-played history (~50 tracks)")
    print()
    
    print("6. Clear Database")
    print("   Deletes ALL data from the database.")
    print("   ⚠️  This removes all songs, artists, albums, and stats!")
    print("   Requires confirmation before proceeding.")
    print()
    
    print("7. Help")
    print("   Shows this help screen with descriptions of all options.")
    print()
    
    print("8. Exit Menu")
    print("   Closes the menu interface.")
    print("   Note: This does NOT stop the Flask app if it's running.")
    print("   Use option 2 first if you want to stop everything.")
    
    print("\n" + "="*60)
    input("\nPress Enter to return to menu...")

def show_menu():
    """Display the main menu"""
    clear_screen()
    print("\n" + "="*60)
    print("     Kungungalacorgus.stats - Backend Menu")
    print("="*60)
    
    # Show current status
    flask_running, ngrok_running = check_if_running()
    
    print("\n Status:")
    print(f"   Flask: {'🟢 Running' if flask_running else '🔴 Stopped'}")
    print(f"   Ngrok: {'🟢 Running' if ngrok_running else '🔴 Stopped'}")
    
    print("\n" + "-"*60)
    print(" Options:")
    print("-"*60)
    print("  1. Start Application")
    print("  2. Stop Application")
    print("  3. Check Background Processes")
    print("  4. Check Database")
    print("  5. Populate Database")
    print("  6. Clear Database")
    print("  7. Help")
    print("  8. Exit Menu")
    print("-"*60)

def main():
    """Main menu loop"""
    while True:
        show_menu()
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            start_application()
        elif choice == '2':
            stop_application()
        elif choice == '3':
            check_background()
        elif choice == '4':
            check_database_menu()
        elif choice == '5':
            populate_database_menu()
        elif choice == '6':
            clear_database_menu()
        elif choice == '7':
            help_menu()
        elif choice == '8':
            clear_screen()
            print("\n✓ Goodbye!\n")
            sys.exit(0)
        else:
            input("\n✗ Invalid choice. Press Enter to try again...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("\n\n✓ Goodbye!\n")
        sys.exit(0)
