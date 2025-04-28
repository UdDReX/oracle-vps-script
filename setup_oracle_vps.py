import os
import subprocess
import stat
import json
from getpass import getpass

def setup_environment():
    # Define directories and paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    ssh_dir = os.path.join(base_dir, "ssh_keys")
    config_path = os.path.join(base_dir, "config.json")
    ssh_pub_key = os.path.join(ssh_dir, "id_rsa.pub")
    ssh_priv_key = os.path.join(ssh_dir, "id_rsa")

    # Step 1: Create directories and SSH keys (first run only)
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created directory: {logs_dir}")

    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        print(f"Created directory: {ssh_dir}")

    if not os.path.exists(ssh_pub_key) or not os.path.exists(ssh_priv_key):
        print("Generating new SSH key pair...")
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", "oracle-vps@auto-generated",
            "-f", ssh_priv_key, "-N", ""
        ], check=True)
        os.chmod(ssh_priv_key, stat.S_IRUSR | stat.S_IWUSR)  # 600
        print(f"SSH keys generated at {ssh_pub_key} and {ssh_priv_key}")

    # Step 2: Handle config setup (first run or if config is incomplete)
    if not os.path.exists(config_path) or os.path.getsize(config_path) == 0:
        print("Setting up configuration. Please enter the following details:")
        
        config = {
            "telegram_bot_token": input("Enter Telegram Bot Token: "),
            "telegram_chat_id": input("Enter Telegram Chat ID: "),
            "compartment_id": input("Enter OCI Compartment ID: "),
            "subnet_id": input("Enter OCI Subnet ID: "),
            "availability_domain": input("Enter OCI Availability Domain: "),
            "shape": input("Enter OCI Shape (e.g., VM.Standard.A1.Flex): ") or "VM.Standard.A1.Flex",
            "ocpus": int(input("Enter number of OCPUs (e.g., 4): ") or 4),
            "memory_in_gbs": int(input("Enter memory in GBs (e.g., 24): ") or 24),
            "instance_name": input("Enter instance name (e.g., oracle-vps-instance): ") or "oracle-vps-instance",
            "operating_system": input("Enter operating system (e.g., Canonical Ubuntu): ") or "Canonical Ubuntu",
            "operating_system_version": input("Enter OS version (e.g., 24.04): ") or "24.04",
            "ssh_public_key_path": ssh_pub_key,
            "max_retries": int(input("Enter max retries (e.g., 1000): ") or 1000),
            "retry_interval": int(input("Enter retry interval in seconds (e.g., 60): ") or 60)
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {config_path}. Please review and rerun this script.")
        return  # Exit after first run to let user verify config

    # Step 3: Validate config and run Docker (subsequent runs)
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        # Basic validation
        required_fields = ["telegram_bot_token", "telegram_chat_id", "compartment_id", "subnet_id", "availability_domain"]
        if not all(field in config and config[field] for field in required_fields):
            raise ValueError("Config file is incomplete. Please check and rerun setup.")
        
        print("Configuration validated. Building Docker image...")
        subprocess.run(["docker", "build", "-t", "oracle-vps-script", "."], check=True)
        
        print("Running Docker container...")
        subprocess.run([
            "docker", "run", "-d", "--name", "oracle-vps",
            "-v", f"{base_dir}/logs:/app/logs",
            "--dns", "8.8.8.8", "--restart", "unless-stopped",
            "oracle-vps-script"
        ], check=True)
        print("Setup complete! Use Telegram to interact with the script (/start to begin).")
    
    except json.JSONDecodeError:
        print("Error: config.json is corrupted. Please delete it and rerun setup.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Docker setup: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    setup_environment()