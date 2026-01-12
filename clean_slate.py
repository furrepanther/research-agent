import os
import shutil
import time
import sys

DATA_DIR = r"F:\Antigravity_Results\Research_Papers\data"
DB_PATH = os.path.join(DATA_DIR, "metadata.db")
PAPERS_DIR = os.path.join(DATA_DIR, "papers")

def robust_remove_file(path, retries=5):
    for i in range(retries):
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Deleted file: {path}")
            return True
        except Exception as e:
            print(f"[Attempt {i+1}] Failed to delete {path}: {e}")
            time.sleep(1)
    return False

def robust_remove_dir(path, retries=5):
    for i in range(retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Deleted directory: {path}")
            return True
        except Exception as e:
            print(f"[Attempt {i+1}] Failed to delete directory {path}: {e}")
            time.sleep(1)
    return False

def clean_system():
    print("Starting robust system clean...", flush=True)
    
    # 1. Kill any lingering python processes first (simulating what run_command does but explicit here if needed, 
    # but relies on external kill. We assume main process is killed).
    
    # 2. Delete DB
    if not robust_remove_file(DB_PATH):
        print("CRITICAL ERROR: Could not delete database. Exiting.")
        sys.exit(1)

    # 3. Delete Papers
    if not robust_remove_dir(PAPERS_DIR):
        print("CRITICAL ERROR: Could not delete papers directory. Exiting.")
        sys.exit(1)
        
    # 4. Verification and Re-creation
    time.sleep(1)
    if os.path.exists(DB_PATH) or os.path.exists(PAPERS_DIR):
         print("VERIFICATION FAILED: Files still exist.")
         sys.exit(1)
         
    os.makedirs(PAPERS_DIR, exist_ok=True)
    print("SUCCESS: System cleaned and ready for fresh start.")

if __name__ == "__main__":
    clean_system()
