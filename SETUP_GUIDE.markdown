# Setup Guide for Oracle VPS Creation Script

This guide walks you through gathering all the necessary credentials and setting up your environment to use the Oracle VPS Creation Script.

## Step 1: Set Up an Oracle Cloud Account
1. **Create an Account**:
   - Go to [Oracle Cloud](https://www.oracle.com/cloud/) and sign up for a free account.
   - You’ll get access to the Always Free tier, which includes shapes like `VM.Standard.A1.Flex`.

2. **Set Up OCI Configuration**:
   - Follow Oracle’s guide to [set up your OCI configuration file](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm).
   - Typically, the config file is located at `~/.oci/config` and looks like this:
     ```
     [DEFAULT]
     user=ocid1.user.oc1..your-user-ocid
     fingerprint=your-fingerprint
     key_file=/path/to/your/private-key.pem
     tenancy=ocid1.tenancy.oc1..your-tenancy-ocid
     region=ap-singapore-1
     ```
   - Ensure this file is set up before running the script.

3. **Gather OCI Credentials**:
   - **Compartment ID**:
     - Go to the OCI Console, navigate to *Identity & Security > Compartments*.
     - Select your compartment (or create one) and copy the OCID (e.g., `ocid1.compartment.oc1..your-compartment-id`).
   - **Subnet ID**:
     - Go to *Networking > Virtual Cloud Networks (VCNs)*.
     - Create or select a VCN, then create a subnet (e.g., in the `10.0.0.0/24` CIDR block).
     - Copy the subnet OCID (e.g., `ocid1.subnet.oc1..your-subnet-id`).
   - **Availability Domain**:
     - Go to *Compute > Instances*, click *Create Instance*, and note the availability domain (e.g., `abc:AP-SINGAPORE-1-AD-1`).
     - Use the format shown in the dropdown (not the OCID).

## Step 2: Set Up a Telegram Bot
1. **Create a Bot**:
   - Open Telegram and search for `@BotFather`.
   - Send `/start` and then `/newbot`.
   - Follow the prompts to name your bot (e.g., `OracleVPSScriptBot`).
   - BotFather will give you a bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).

2. **Get Your Chat ID**:
   - Add your bot to a chat or start a private chat with it.
   - Send a message to the bot (e.g., `/start`).
   - Use a service like `@getidsbot` in the same chat to get your chat ID (e.g., `123456789`).

## Step 3: Install Docker
- **Linux**:
  ```bash
  sudo apt update
  sudo apt install docker.io
  sudo systemctl start docker
  sudo systemctl enable docker
  sudo usermod -aG docker $USER
  ```
  Log out and back in to apply the group change.
- **Windows/Mac**:
  - Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop).
  - Start Docker Desktop and ensure it’s running.

## Step 4: Install Python
- The setup script requires Python 3.9+.
- **Linux**:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip
  ```
- **Windows/Mac**:
  - Download and install Python from [python.org](https://www.python.org/downloads/).
  - Ensure `pip` is installed and Python is added to your PATH.

## Step 5: Prepare Your Environment
- Ensure you have `git` installed to clone the repository:
  ```bash
  sudo apt install git  # Linux
  ```
  For Windows/Mac, download Git from [git-scm.com](https://git-scm.com/downloads).

## Step 6: Gather Configuration Details
During the first run of `setup_oracle_vps.py`, you’ll be prompted for:
- **Telegram Bot Token**: From BotFather.
- **Telegram Chat ID**: From your chat.
- **OCI Compartment ID**, **Subnet ID**, **Availability Domain**: From the OCI Console.
- **Shape**, **OCPUs**, **Memory**: Defaults are provided (e.g., `VM.Standard.A1.Flex`, 4 OCPUs, 24 GB). Adjust based on your needs.
- **Instance Name**, **Operating System**, **OS Version**: Defaults are provided (e.g., `oracle-vps-instance`, `Canonical Ubuntu`, `24.04`).
- **Max Retries**, **Retry Interval**: Defaults are 1000 retries and 60 seconds.

## Step 7: Run the Script
Follow the instructions in [README.md](README.md) to clone the repository and run `setup_oracle_vps.py`.

## Troubleshooting Tips
- **OCI Setup Issues**:
  - Double-check your `~/.oci/config` file for accuracy.
  - Ensure your compartment has sufficient quotas for the chosen shape.
- **Telegram Issues**:
  - Ensure your bot token is correct and the bot is added to your chat.
  - Test sending `/start` to the bot manually to confirm it responds.
- **Docker Issues**:
  - Verify Docker is running (`docker info`).
  - Ensure you have permissions to run Docker commands.