# Installation Guide

This guide covers installation of SSH Tunnel Auto-Tester on various platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Linux Installation](#linux-installation)
- [macOS Installation](#macos-installation)
- [Windows (WSL) Installation](#windows-wsl-installation)
- [Docker Installation](#docker-installation)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Python Version
- Python 3.8 or higher

### System Requirements
- 50MB disk space
- Network access (for testing tunnels)
- Root/sudo access (for some features)

## Linux Installation

### Ubuntu/Debian

```bash
# Update package list
sudo apt-get update

# Install Python and pip
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies for full functionality
sudo apt-get install -y \
    openssh-client \
    stunnel4 \
    corkscrew \
    proxytunnel \
    netcat-openbsd \
    curl \
    jq

# Clone the repository
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python tunnel_tester.py --version
```

### Fedora/RHEL/CentOS

```bash
# Install Python and pip
sudo dnf install -y python3 python3-pip

# Install system dependencies
sudo dnf install -y \
    openssh-clients \
    stunnel \
    nc \
    curl \
    jq

# Clone and install
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Arch Linux

```bash
# Install dependencies
sudo pacman -S python python-pip openssh stunnel netcat curl jq

# Clone and install
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## macOS Installation

### Using Homebrew

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and dependencies
brew install python3 stunnel netcat curl jq

# Install corkscrew (HTTP tunneling)
brew install corkscrew

# Clone the repository
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python tunnel_tester.py --version
```

## Windows (WSL) Installation

SSH Tunnel Auto-Tester works on Windows through WSL (Windows Subsystem for Linux).

### Step 1: Install WSL

```powershell
# Run in PowerShell as Administrator
wsl --install
```

Restart your computer after installation.

### Step 2: Install in WSL

```bash
# Open WSL terminal and follow Linux installation steps
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv openssh-client stunnel4 netcat-openbsd

git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Docker Installation

### Using Pre-built Image

```bash
# Pull the image
docker pull your-repo/ssh-tunnel-auto-tester:latest

# Run with config file
docker run -v $(pwd)/config.yaml:/app/config.yaml \
    your-repo/ssh-tunnel-auto-tester --auto
```

### Building Locally

```bash
# Clone repository
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester

# Build Docker image
docker build -t ssh-tunnel-tester .

# Run
docker run -v $(pwd)/config.yaml:/app/config.yaml ssh-tunnel-tester --auto
```

### Using Docker Compose

```bash
# Create config.yaml first
cp config.yaml.example config.yaml
# Edit config.yaml with your settings

# Run with docker-compose
docker-compose up
```

## Verifying Installation

### Test Python Installation

```bash
# Check version
python tunnel_tester.py --version

# List available methods
python tunnel_tester.py --list-methods

# Check network detection
python tunnel_tester.py --detect-network
```

### Test Bash Installation

```bash
# Check version
bash bash/tunnel_tester.sh --version

# List available methods
bash bash/tunnel_tester.sh --list-methods

# Check dependencies
bash bash/tunnel_tester.sh --check-deps
```

## Optional Dependencies

Some advanced features require additional packages:

### For DNS Tunneling
```bash
# Requires iodine (server-side setup needed)
sudo apt-get install iodine
```

### For SOCKS Proxy Support
```bash
pip install PySocks
```

### For Scapy (Network Analysis)
```bash
# Requires root privileges for some features
pip install scapy
```

## Troubleshooting

### "Command not found" Errors

Make sure Python is in your PATH:
```bash
which python3
# Should output something like /usr/bin/python3
```

### Permission Denied

Some features require elevated privileges:
```bash
sudo python tunnel_tester.py --auto
```

### Missing Dependencies

Check which methods are available:
```bash
python tunnel_tester.py --list-methods
```

Install missing dependencies as indicated.

### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### SSL/Certificate Errors

If you get SSL certificate errors:
```bash
pip install --upgrade certifi
```

## Next Steps

After installation:

1. Copy and edit the configuration file:
   ```bash
   cp config.yaml.example config.yaml
   nano config.yaml
   ```

2. See [CONFIGURATION.md](CONFIGURATION.md) for configuration options

3. Run your first test:
   ```bash
   python tunnel_tester.py --auto
   ```

4. See [README.md](../README.md) for usage examples
