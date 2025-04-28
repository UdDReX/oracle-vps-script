# Oracle VPS Creation Script

This script automates the creation of an Oracle Cloud Infrastructure (OCI) VPS instance using the `VM.Standard.A1.Flex` shape (or others). It retries on "Out of host capacity" errors and sends updates via Telegram.

## Prerequisites
- An Oracle Cloud account with a compartment, subnet, and SSH keys set up.
- A Telegram bot and chat ID (create one via BotFather on Telegram).
- Docker installed on your system.

## Setup
1. **Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/oracle-vps-script.git
   cd oracle-vps-script
   ```

2. **Configure the Script**
   - Copy `config.json` to the project root.
   - Fill in your details:
     - `telegram_bot_token`: Your Telegram bot token.
     - `telegram_chat_id`: Your Telegram chat ID.
     - OCI credentials (`compartment_id`, `subnet_id`, `availability_domain`).
     - `ssh_public_key_path`: Path to your SSH public key (default: `/app/ssh_keys/id_rsa.pub`).
     - Adjust `shape`, `ocpus`, `memory_in_gbs`, `max_retries`, and `retry_interval` as needed.

3. **Add SSH Keys**
   - Place your SSH public key in `ssh_keys/id_rsa.pub`.

4. **Build and Run the Docker Container**
   ```bash
   docker build -t oracle-vps-script .
   docker run -d --name oracle-vps -v $(pwd)/logs:/app/logs --dns 8.8.8.8 --restart unless-stopped oracle-vps-script
   ```

5. **Interact via Telegram**
   - Send `/start` to your bot to begin instance creation.
   - Send `/stop` to stop the script.

## Logs
- Logs are saved to the `logs/oracle_vps.log` file for debugging.

## Notes
- The script caches the image ID for 24 hours to avoid repeated API calls.
- It automatically selects an Arm image for Arm shapes (like `VM.Standard.A1.Flex`).

## Troubleshooting
- Ensure your OCI credentials are correct and have sufficient permissions.
- Check the logs in `logs/oracle_vps.log` for errors.
- Verify your Telegram bot token and chat ID are correct.

## License
MIT License