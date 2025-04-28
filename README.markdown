# Oracle VPS Creation Script

This script automates the creation of an Oracle Cloud Infrastructure (OCI) VPS instance, such as the `VM.Standard.A1.Flex` shape (or others). It includes retry logic for "Out of host capacity" errors and sends status updates via Telegram.

## Overview
The script is designed to simplify the process of creating an OCI VPS instance, especially for free-tier users who often face capacity issues. It:
- Automatically selects the appropriate image (e.g., Arm image for Arm shapes).
- Retries instance creation on capacity errors (default: 1000 retries, 60-second intervals).
- Sends notifications via Telegram for success, retries, or failures.
- Caches image IDs to reduce API calls.

## Prerequisites
Before starting, ensure you have:
- An Oracle Cloud account with a compartment, subnet, and SSH keys set up.
- A Telegram bot and chat ID (create one via BotFather on Telegram).
- Docker installed on your system.
- Python 3.9+ installed for running the setup script.

For detailed instructions on gathering these requirements, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Directory Structure
After setup, your project directory should look like this:
```
oracle-vps-script/
├── create_oracle_vps.py  # Main script for creating the VPS
├── setup_oracle_vps.py   # Setup script to initialize the environment
├── Dockerfile            # Docker configuration
├── config.json           # Configuration file (generated during setup)
├── logs/                 # Directory for logs (generated)
│   └── instance_creation.log  # Log file
├── ssh_keys/             # Directory for SSH keys (generated)
│   ├── id_rsa            # Private key
│   └── id_rsa.pub        # Public key
├── README.md             # This file
└── SETUP_GUIDE.md        # Guide for gathering credentials
```

## Setup and Usage
Follow these steps to set up and run the script.

### Step 1: Clone the Repository
Clone the project to your local machine:
```bash
git clone https://github.com/YOUR_USERNAME/oracle-vps-script.git
cd oracle-vps-script
```

### Step 2: Run the Setup Script (First Time)
The setup script will create directories, generate SSH keys, and prompt you for configuration details.
```bash
python setup_oracle_vps.py
```
- **What happens**:
  - Creates `logs` and `ssh_keys` directories.
  - Generates an SSH key pair if none exists.
  - Creates necessary files (`create_oracle_vps.py`, `Dockerfile`, etc.) if missing.
  - Prompts you to enter details like Telegram bot token, OCI credentials, etc.
  - Saves the configuration to `config.json`.
- **Next step**: Review the generated `config.json` file to ensure all details are correct.

### Step 3: Run the Setup Script Again (Subsequent Runs)
Rerun the setup script to build and run the Docker container:
```bash
python setup_oracle_vps.py
```
- **What happens**:
  - Validates `config.json` for required fields.
  - Builds the Docker image (`oracle-vps-script`).
  - Runs the container with proper volume mapping for logs.
- **Outcome**: The script is now running in a Docker container and listening for Telegram commands.

### Step 4: Interact via Telegram
Use Telegram to control the script. See the "Telegram Bot Commands" section for available commands.

### Step 5: Monitor Logs
Check the logs for debugging or to monitor progress:
- Logs are stored in `logs/instance_creation.log`.
- Example log entries:
  ```
  2025-04-28 15:11:00 - INFO - Using image: Canonical-Ubuntu-24.04-aarch64-2025.03.28-0 (ID: ...)
  2025-04-28 15:12:00 - ERROR - Attempt 1: Out of host capacity. Retrying...
  ```

## Telegram Bot Commands
Interact with the script using the following Telegram commands. Send these commands to your bot in the configured chat.

- **`/start`**:
  - **Description**: Initiates the instance creation process.
  - **Usage**: Send `/start` to the bot.
  - **Response**: The bot will reply with "Started instance creation process" and provide updates (e.g., image used, retry attempts).
  - **Notes**: The script will retry up to the configured `max_retries` if it encounters "Out of host capacity" errors. If a process is already running, it will notify you.

- **`/stop`**:
  - **Description**: Stops the instance creation process.
  - **Usage**: Send `/stop` to the bot.
  - **Response**: The bot will reply with "Stopped instance creation process."
  - **Notes**: This stops the script from retrying but does not terminate the Docker container. Restart the container by rerunning `python setup_oracle_vps.py`.

- **`/status`**:
  - **Description**: Checks the current status of the instance creation process.
  - **Usage**: Send `/status` to the bot.
  - **Response**: The bot will reply with either "Instance creation is running" or "Instance creation is stopped. Last instance OCID: [OCID or None]."
  - **Notes**: Useful for checking if the script is actively trying to create an instance.

- **`/getid`**:
  - **Description**: Retrieves the chat ID of the current Telegram chat.
  - **Usage**: Send `/getid` to the bot.
  - **Response**: The bot will reply with "Your chat ID is: [chat_id]."
  - **Notes**: Helpful for verifying the chat ID to use in `config.json`.

- **`/config`**:
  - **Description**: Updates the configuration settings in `config.json`.
  - **Usage**: Send `/config {json_data}` in the admin group specified in `telegram_admin_group_id`.
  - **Example**: `/config {"retry_interval": 30, "max_retries": 500}`
  - **Response**: The bot will reply with "Configuration updated successfully" or an error message if the update fails.
  - **Notes**: 
    - This command is restricted to the admin group specified in `config.json`.
    - The `json_data` must be a valid JSON string with key-value pairs to update the configuration.

## Configuration Options
The `config.json` file contains the following fields:
- `telegram_bot_token`: Your Telegram bot token.
- `telegram_chat_id`: Your Telegram chat ID.
- `telegram_admin_group_id`: The Telegram group ID where `/config` commands are allowed.
- `compartment_id`: OCI compartment ID.
- `subnet_id`: OCI subnet ID.
- `availability_domain`: OCI availability domain.
- `shape`: Instance shape (e.g., `VM.Standard.A1.Flex`).
- `ocpus`: Number of OCPUs (e.g., 2).
- `memory_in_gbs`: Memory in GBs (e.g., 12).
- `instance_name`: Name of the instance (e.g., `PelicanVPS`).
- `operating_system`: OS to use (e.g., `Canonical Ubuntu`).
- `operating_system_version`: OS version (e.g., `24.04`).
- `ssh_public_key_path`: Path to your SSH public key (auto-generated).
- `retry_interval`: Seconds between retries (e.g., 60).
- `max_retries`: Maximum retry attempts (e.g., 1000).

You can edit `config.json` directly if needed, then rerun `python setup_oracle_vps.py`.

## Notes
- The script caches the image ID for 24 hours to reduce API calls.
- It automatically selects an Arm image for Arm shapes (like `VM.Standard.A1.Flex`).
- If an existing `id_rsa` or `id_rsa.pub` is found in `ssh_keys`, it will be used; otherwise, new keys are generated.

## Troubleshooting
- **Config Errors**: If `config.json` is incomplete or corrupted, delete it and rerun `python setup_oracle_vps.py` to regenerate it.
- **OCI Errors**: Ensure your credentials have sufficient permissions. Check `logs/instance_creation.log` for details.
- **Telegram Issues**: Verify your bot token and chat ID. Ensure the bot is added to your chat.
- **Docker Issues**: Ensure Docker is installed and running. Check for errors during the build/run process.

## Contributing
Feel free to open issues or submit pull requests on GitHub to improve the script!

## License
[MIT License](LICENSE)
