import os
import json
import time
from datetime import datetime, timedelta
import logging
import oci
from telegram import Bot
import asyncio

# Constants
CACHE_FILE = "/app/cache/image_cache.json"

# Setup logging
logging.basicConfig(
    filename='/app/logs/oracle_vps.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration from config.json
with open('/app/config.json', 'r') as f:
    config = json.load(f)

# Initialize OCI Compute Client
config_oci = oci.config.from_file()
compute_client = oci.core.ComputeClient(config_oci)

# Initialize Telegram Bot
bot = Bot(token=config['telegram_bot_token'])

def get_image_id():
    """Fetch the latest compatible image ID for the specified OS and shape."""
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
        cache.get('shape') == config['shape'] and
        cache.get('timestamp') and
        datetime.fromisoformat(cache['timestamp']) > datetime.now() - timedelta(days=1)):
        return cache['image_id']

    # Fetch images using OCI SDK
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

    # Filter for Arm images if using an Arm shape
    if config['shape'].startswith('VM.Standard.A1'):
        selected_images = [img for img in images if "aarch64" in img.display_name.lower()]
    else:
        selected_images = [img for img in images if "aarch64" not in img.display_name.lower()]

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
        'shape': config['shape'],
        'image_id': image_id,
        'timestamp': datetime.now().isoformat()
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)
    bot.send_message(config['telegram_chat_id'],
                     f"Using image: {latest_image.display_name} (Created: {latest_image.time_created.strftime('%Y-%m-%d')})")
    return image_id

def create_instance():
    """Create an Oracle Cloud instance with retry logic for capacity issues."""
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

async def handle_telegram_updates():
    """Handle Telegram commands to start/stop instance creation."""
    offset = None
    while True:
        updates = await bot.get_updates(offset=offset)
        for update in updates:
            offset = update.update_id + 1
            if update.message and update.message.chat.id == int(config['telegram_chat_id']):
                command = update.message.text.lower()
                if command == '/start':
                    await bot.send_message(config['telegram_chat_id'], "Started instance creation process.")
                    try:
                        create_instance()
                    except Exception as e:
                        logger.error(f"Failed to create instance: {e}")
                        await bot.send_message(config['telegram_chat_id'], f"Failed to create instance: {e}")
                elif command == '/stop':
                    await bot.send_message(config['telegram_chat_id'], "Stopping script.")
                    os._exit(0)

if __name__ == "__main__":
    asyncio.run(handle_telegram_updates())