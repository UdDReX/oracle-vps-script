import os
import subprocess
import stat
import json
from getpass import getpass


def create_file_if_not_exists(file_path, content):
    """Create a file with the given content if it doesn't exist."""
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created file: {file_path}")


def setup_environment():
    # Define directories and paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    ssh_dir = os.path.join(base_dir, "ssh_keys")
    config_path = os.path.join(base_dir, "config.json")
    create_script_path = os.path.join(base_dir, "create_oracle_vps.py")
    dockerfile_path = os.path.join(base_dir, "Dockerfile")
    readme_path = os.path.join(base_dir, "README.md")
    guide_path = os.path.join(base_dir, "SETUP_GUIDE.md")
    ssh_pub_key = os.path.join(ssh_dir, "id_rsa.pub")
    ssh_priv_key = os.path.join(ssh_dir, "id_rsa")

    # Step 1: Create directories
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created directory: {logs_dir}")

    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        print(f"Created directory: {ssh_dir}")

    # Step 2: Generate SSH keys if missing
    if not os.path.exists(ssh_pub_key) or not os.path.exists(ssh_priv_key):
        print("Generating new SSH key pair...")
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", "oracle-vps@auto-generated",
            "-f", ssh_priv_key, "-N", ""
        ], check=True)
        os.chmod(ssh_priv_key, stat.S_IRUSR | stat.S_IWUSR)  # 600
        print(f"SSH keys generated at {ssh_pub_key} and {ssh_priv_key}")

    # Step 3: Create necessary files if missing
    create_script_content = """import oci
import json
import time
import logging
import os
import telegram
from telegram.ext import Updater, CommandHandler
from threading import Thread
from datetime import datetime, timedelta


# Setup logging
logging.basicConfig(
    filename="/app/logs/instance_creation.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Load configuration
def load_config():
    default_config = {
        "operating_system": "Canonical Ubuntu",
        "operating_system_version": "24.04",
        "shape": "VM.Standard.A1.Flex",
        "ocpus": 2,
        "memory_in_gbs": 12,
        "region": "ap-singapore-1",
        "compartment_id": "ocid1.tenancy.oc1..aaaaaaaahcq6l2omxpd3z6ffu3w4ajw6rrvfcrbb5mkwjcgji4qdctepaqaa",
        "vcn_id": "ocid1.vcn.oc1.ap-singapore-1.amaaaaaax3pjiaqaii37frr3lnplrbkuzdb7ra47gxouhk5a7sqsh6h6rkuq",
        "subnet_id": "ocid1.subnet.oc1.ap-singapore-1.aaaaaaaanlyyocqvvtcwzhvx2kn7io4v26vxdjy4cyxnxtmdu4cdmaia6tra",
        "ssh_public_key_path": "/app/ssh_keys/id_rsa.pub",
        "instance_name": "PelicanVPS",
        "retry_interval": 60,
        "max_retries": 1000,
        "telegram_bot_token": "8029470448:AAHPFmELthaEo0ErpF7Ry6yiXK7LvSmZLRY",
        "telegram_chat_id": "66792440733",
        "telegram_admin_group_id": "-4647964334",
        "availability_domain": "ISAb:AP-SINGAPORE-1-AD-1"
    }
    config_file = "/app/config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        default_config.update(config)
    else:
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
    return default_config


config = load_config()

# Initialize Telegram bot
bot = telegram.Bot(token=config['telegram_bot_token'])

# Oracle Cloud client
oci_config_path = "/app/oci_config"
oci.config.validate_config(oci.config.from_file(file_location=oci_config_path))
compute_client = oci.core.ComputeClient(oci.config.from_file(file_location=oci_config_path))
network_client = oci.core.VirtualNetworkClient(oci.config.from_file(file_location=oci_config_path))

# Global state
running = False
instance_ocid = None

# Cache file for image ID
CACHE_FILE = "/app/image_cache.json"


# Generate or load SSH key
def get_ssh_key():
    ssh_key_path = config['ssh_public_key_path']
    private_key_path = ssh_key_path.replace('.pub', '')
    if not os.path.exists(ssh_key_path):
        logger.warning("SSH public key not found. Generating new key pair.")
        os.makedirs(os.path.dirname(ssh_key_path), exist_ok=True)
        os.system(f"ssh-keygen -t rsa -b 2048 -f {private_key_path} -N ''")
        bot.send_message(config['telegram_chat_id'], "SSH key pair generated at /app/ssh/")
    with open(ssh_key_path, 'r') as f:
        ssh_key = f.read().strip()
    return ssh_key


# Find the latest image ID and cache it
def get_image_id():
    # Initialize cache if empty or invalid
    if not os.path.exists(CACHE_FILE) or os.path.getsize(CACHE_FILE) == 0:
        with open(CACHE_FILE, 'w') as f:
            json.dump({}, f)

    # Check cache first
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, ValueError):
        cache = {}

    if (cache.get('operating_system') == config['operating_system'] and
        cache.get('operating_system_version') == config['operating_system_version'] and
        cache.get('shape') == config['shape'] and  # Add shape to cache check
        cache.get('timestamp') and
        datetime.fromisoformat(cache['timestamp']) > datetime.now() - timedelta(days=1)):
        return cache['image_id']

    # Use OCI SDK to fetch all images with specific OS filter
    from oci.pagination import list_call_get_all_results
    images = list_call_get_all_results(
        compute_client.list_images,
        compartment_id=config['compartment_id'],
        operating_system=config['operating_system'],
        operating_system_version=config['operating_system_version']
    ).data

    logger.info(f"Found {len(images)} images matching OS: {config['operating_system']} {config['operating_system_version']}")

    # Log all image details for debugging
    for image in images:
        logger.info(f"Image: {image.display_name} (ID: {image.id}, Created: {image.time_created})")

    # Filter for Arm images if using an Arm shape (e.g., VM.Standard.A1.Flex)
    if config['shape'].startswith('VM.Standard.A1'):
        selected_images = [img for img in images if "aarch64" in img.display_name.lower()]
    else:
        selected_images = [img for img in images if "aarch64" not in img.display_name.lower()]

    # Use all images if no match found for the shape
    if not selected_images:
        selected_images = images
        logger.warning(f"No matching architecture images for shape {config['shape']}. Using all available images.")

    # Sort by creation time and pick the latest
    if selected_images:
        latest_image = max(selected_images, key=lambda img: img.time_created)
        logger.info(f"Using image: {latest_image.display_name} (ID: {latest_image.id})")
    else:
        raise ValueError(f"No images found for {config['operating_system']} {config['operating_system_version']}")

    # Cache and notify
    image_id = latest_image.id
    cache = {
        'operating_system': config['operating_system'],
        'operating_system_version': config['operating_system_version'],
        'shape': config['shape'],  # Cache shape too
        'image_id': image_id,
        'timestamp': datetime.now().isoformat()
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)
    bot.send_message(config['telegram_chat_id'],
                     f"Using image: {latest_image.display_name} (Created: {latest_image.time_created.strftime('%Y-%m-%d')})")
    return image_id


# Create Oracle Cloud instance
def create_instance():
    image_id = get_image_id()
    instance_details = oci.core.models.LaunchInstanceDetails(
        compartment_id=config['compartment_id'],
        display_name=config['instance_name'],
        shape=config['shape'],
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=config['ocpus'],
            memory_in_gbs=config['memory_in_gbs']
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            image_id=image_id
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=config['subnet_id'],
            display_name="Primary VNIC"
        ),
        availability_domain=config['availability_domain'],
        metadata={
            "ssh_authorized_keys": open(config['ssh_public_key_path']).read()
        }
    )

    for attempt in range(config['max_retries']):
        try:
            instance = compute_client.launch_instance(instance_details).data
            logger.info(f"Instance created: {instance.id}")
            bot.send_message(config['telegram_chat_id'], f"Instance created: {instance.id}")
            return instance
        except oci.exceptions.ServiceError as e:
            if e.status == 500 and "Out of host capacity" in e.message:
                logger.error(f"Attempt {attempt + 1}: Out of host capacity. Retrying...")
                bot.send_message(config['telegram_chat_id'], f"Attempt {attempt + 1}: Out of host capacity. Retrying...")
                time.sleep(config['retry_interval'])
            else:
                logger.error(f"Error creating instance: {e}")
                bot.send_message(config['telegram_chat_id'], f"Error creating instance: {e}")
                raise
    else:
        logger.error("Max retries reached. Stopping.")
        bot.send_message(config['telegram_chat_id'], "Max retries reached. Stopping.")
        raise Exception("Max retries reached. Could not create instance.")


# Telegram command handlers
def start(update, context):
    global running
    if not running:
        running = True
        Thread(target=create_instance).start()
        update.message.reply_text("Started instance creation process.")
    else:
        update.message.reply_text("Instance creation is already running.")


def stop(update, context):
    global running
    running = False
    update.message.reply_text("Stopped instance creation process.")


def status(update, context):
    if running:
        update.message.reply_text("Instance creation is running.")
    else:
        update.message.reply_text(f"Instance creation is stopped. Last instance OCID: {instance_ocid or 'None'}")


def getid(update, context):
    update.message.reply_text(f"Your chat ID is: {update.message.chat_id}")


def config_command(update, context):
    if str(update.message.chat_id) != config['telegram_admin_group_id']:
        update.message.reply_text("This command is only available in the admin group.")
        return
    try:
        new_config = json.loads(' '.join(context.args))
        with open('/app/config.json', 'r') as f:
            current_config = json.load(f)
        current_config.update(new_config)
        with open('/app/config.json', 'w') as f:
            json.dump(current_config, f, indent=4)
        config = load_config()
        update.message.reply_text("Configuration updated successfully.")
    except Exception as e:
        update.message.reply_text(f"Error updating config: {str(e)}")


# Main function
def main():
    updater = Updater(config['telegram_bot_token'], use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("getid", getid))
    dp.add_handler(CommandHandler("config", config_command))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
"""

    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

RUN pip install oci python-telegram-bot

COPY create_oracle_vps.py .
COPY config.json .
COPY ssh_keys/ ./ssh_keys/

CMD ["python", "create_oracle_vps.py"]
"""
    create_file_if_not_exists(create_script_path, create_script_content)
    create_file_if_not_exists(dockerfile_path, dockerfile_content)
    create_file_if_not_exists(readme_path, readme_content)
    create_file_if_not_exists(guide_path, guide_content)

    # Step 4: Handle config setup (first run or if config is incomplete)
    if not os.path.exists(config_path) or os.path.getsize(config_path) == 0:
        print("Setting up configuration. Please enter the following details:")

        config = {
            "telegram_bot_token": input("Enter Telegram Bot Token: "),
            "telegram_chat_id": input("Enter Telegram Chat ID: "),
            "telegram_admin_group_id": input("Enter Telegram Admin Group ID: "),
            "compartment_id": input("Enter OCI Compartment ID: "),
            "subnet_id": input("Enter OCI Subnet ID: "),
            "availability_domain": input("Enter OCI Availability Domain: "),
            "shape": input("Enter OCI Shape (e.g., VM.Standard.A1.Flex): ") or "VM.Standard.A1.Flex",
            "ocpus": int(input("Enter number of OCPUs (e.g., 2): ") or 2),
            "memory_in_gbs": int(input("Enter memory in GBs (e.g., 12): ") or 12),
            "instance_name": input("Enter instance name (e.g., PelicanVPS): ") or "PelicanVPS",
            "operating_system": input("Enter operating system (e.g., Canonical Ubuntu): ") or "Canonical Ubuntu",
            "operating_system_version": input("Enter OS version (e.g., 24.04): ") or "24.04",
            "ssh_public_key_path": ssh_pub_key,
            "retry_interval": int(input("Enter retry interval in seconds (e.g., 60): ") or 60),
            "max_retries": int(input("Enter max retries (e.g., 1000): ") or 1000)
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {config_path}. Please review and rerun this script.")
        return  # Exit after first run to let user verify config

    # Step 5: Validate config and run Docker (subsequent runs)
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        required_fields = [
            "telegram_bot_token",
            "telegram_chat_id",
            "telegram_admin_group_id",
            "compartment_id",
            "subnet_id",
            "availability_domain"
        ]
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
