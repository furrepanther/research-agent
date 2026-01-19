import keyring
import getpass
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())
try:
    from src.utils import get_config
except:
    def get_config(): return {}

def setup_keys():
    print("=== Secure Password Setup (Research Agent) ===")
    print("This tool stores your SMTP password in the OS Keyring/Credential Manager")
    print("rather than a plain text config file.\n")
    
    config = get_config()
    default_user = config.get("email", {}).get("smtp_user", "")
    
    username = input(f"Enter SMTP Username [{default_user}]: ").strip() or default_user
    if not username:
        print("Error: Username required.")
        return
        
    password = getpass.getpass(f"Enter SMTP Password for {username}: ")
    if not password:
        print("Operation cancelled.")
        return
        
    try:
        keyring.set_password("research_agent", username, password)
        print(f"\nSuccess! Password for '{username}' stored securely.")
        print("You can debugging verification: python -c \"import keyring; print(keyring.get_password('research_agent', '{username}'))\"")
    except Exception as e:
        print(f"\nError accessing keyring: {e}")
        print("Ensure 'keyring' package is installed (pip install keyring).")

if __name__ == "__main__":
    setup_keys()
