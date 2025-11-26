# SSH Tunnel Auto-Tester

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful, comprehensive SSH tunneling tool that automatically tests multiple methods to establish connections through restricted 4G/mobile networks and find working free data access methods.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Tunneling Methods](#tunneling-methods)
- [Troubleshooting](#troubleshooting)
- [Legal & Ethical Use](#legal--ethical-use)
- [Contributing](#contributing)
- [License](#license)

## Features

### 🚀 Multi-Method Testing
- **Direct SSH** - Standard SSH connection
- **WebSocket Tunnel** - SSH over WebSocket protocol
- **SSL/TLS Wrapper** - SSH wrapped in SSL (stunnel-like)
- **HTTP CONNECT Tunnel** - SSH through HTTP proxies
- **DNS Tunnel** - SSH through DNS queries
- **SNI Spoofing** - Bypass DPI with fake SNI headers
- **Traffic Obfuscation** - Evade traffic analysis

### 🔧 Dual Implementation
- **Python** - Full-featured implementation with rich libraries
- **Bash** - Lightweight alternative for minimal systems

### ⚡ Smart Features
- Parallel testing for speed
- Circuit breaker pattern to avoid IP bans
- Caching of successful methods
- Auto-reconnect on disconnect
- Network type detection (4G/WiFi/Ethernet)
- Connection quality testing

### 📊 Comprehensive Reporting
- Colorized console output
- Detailed logging
- JSON/CSV export
- Success/failure metrics

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester

# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp config.yaml.example config.yaml
nano config.yaml  # Add your SSH server details

# Run auto-test
python tunnel_tester.py --auto
```

Or test with command-line credentials:

```bash
python tunnel_tester.py --host your-ssh-server.com --user your_username --auto
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Linux/macOS

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install -y openssh-client stunnel4 netcat-openbsd

# Clone repository
git clone https://github.com/your-repo/ssh-tunnel-auto-tester.git
cd ssh-tunnel-auto-tester

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Windows (WSL)

```bash
# In WSL terminal, follow Linux instructions above
```

### Docker

```bash
# Build and run
docker build -t ssh-tunnel-tester .
docker run -v $(pwd)/config.yaml:/app/config.yaml ssh-tunnel-tester --auto
```

For detailed installation instructions, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Configuration

Create a `config.yaml` file with your SSH server details:

```yaml
ssh_accounts:
  - host: "your-ssh-server.com"
    port: 22
    username: "your_username"
    password: "your_password"
    # Or use key authentication:
    # key_file: "~/.ssh/id_rsa"

test_modes:
  - direct
  - ssl_wrap
  - websocket
  - http_tunnel
  - sni_spoof

ports_to_test:
  - 22
  - 80
  - 443
  - 8080

timeout: 10
auto_connect: true
```

For full configuration options, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Usage

### Command-Line Arguments

```bash
# Auto-test all methods
python tunnel_tester.py --auto

# Test specific method
python tunnel_tester.py --method websocket --host example.com --user myuser

# Quick test (direct SSH only)
python tunnel_tester.py --host example.com --user myuser --quick

# Find working method and connect
python tunnel_tester.py --find-and-connect

# Test specific ports
python tunnel_tester.py --ports 80,443,8080 --auto

# Verbose mode
python tunnel_tester.py --auto --verbose

# Export results to JSON
python tunnel_tester.py --auto --export results.json

# Interactive mode
python tunnel_tester.py --interactive

# List available methods
python tunnel_tester.py --list-methods

# Detect network type
python tunnel_tester.py --detect-network
```

### Bash Version

```bash
# Auto-test
bash bash/tunnel_tester.sh --auto --config config.yaml

# Test specific method
bash bash/tunnel_tester.sh --method direct --host example.com --user myuser

# List methods
bash bash/tunnel_tester.sh --list-methods
```

### Docker

```bash
# Using docker-compose
docker-compose up

# Or run directly
docker run -v $(pwd)/config.yaml:/app/config.yaml \
    ssh-tunnel-tester --auto
```

### As a Service

```bash
# Copy service file
sudo cp ssh-tunnel-tester.service /etc/systemd/system/

# Edit paths in service file as needed
sudo nano /etc/systemd/system/ssh-tunnel-tester.service

# Enable and start
sudo systemctl enable ssh-tunnel-tester
sudo systemctl start ssh-tunnel-tester
```

## How It Works

### Testing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Start Auto-Test                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Load Configuration & Detect Network            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Check Cache for Previous Success               │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        [Cache Hit]                  [Cache Miss]
              │                           │
              ▼                           ▼
┌─────────────────────┐    ┌─────────────────────────────────┐
│  Try Cached Method  │    │  Test Methods in Priority Order │
└─────────────────────┘    │  ┌─────────────────────────────┐│
              │            │  │ For each method & port:     ││
              │            │  │  1. Check circuit breaker   ││
              │            │  │  2. Attempt connection      ││
              │            │  │  3. Verify SSH banner       ││
              │            │  │  4. Record result           ││
              │            │  └─────────────────────────────┘│
              │            └─────────────────────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Found Working Method?                       │
└─────────────────────────────────────────────────────────────┘
              │                           │
         [Yes]                        [No]
              │                           │
              ▼                           ▼
┌─────────────────────┐    ┌─────────────────────────────────┐
│   Cache Method      │    │     Report All Failures         │
│   Auto-Connect      │    └─────────────────────────────────┘
│   Keep-Alive Loop   │
└─────────────────────┘
```

### Method Priority

For 4G/mobile networks with DPI, recommended testing order:

1. **ssl_wrap** (443) - Looks like HTTPS traffic
2. **sni_spoof** (443) - Evades SNI-based blocking
3. **websocket** (443/80) - Often allowed through firewalls
4. **http_tunnel** (8080) - Uses HTTP CONNECT
5. **direct** (22) - Standard SSH (often blocked)

## Tunneling Methods

### Direct SSH
Standard SSH connection. Works on unrestricted networks but often blocked on 4G/mobile networks.

### WebSocket Tunnel
Encapsulates SSH in WebSocket protocol. Many firewalls allow WebSocket traffic as it's used by modern web applications.

### SSL/TLS Wrapper
Wraps SSH traffic in SSL/TLS, making it appear as regular HTTPS traffic. Uses stunnel-like approach.

### HTTP CONNECT Tunnel
Uses HTTP CONNECT method through a proxy. Works when only HTTP/HTTPS proxies are allowed.

### SNI Spoofing
Sends fake SNI (Server Name Indication) headers to make the connection appear as if it's going to a popular allowed domain (e.g., google.com).

### DNS Tunnel
Encodes data in DNS queries. Works even when only DNS traffic is allowed. Requires server-side setup (e.g., iodine).

### Traffic Obfuscation
Applies various techniques to make traffic patterns unrecognizable to DPI:
- Traffic padding
- Timing randomization
- Packet fragmentation

## Troubleshooting

### Common Issues

**All methods fail:**
```bash
# Check basic connectivity
python tunnel_tester.py --detect-network

# Try with increased timeout
python tunnel_tester.py --auto --timeout 30
```

**Authentication errors:**
```bash
# Test direct SSH first
ssh -v user@your-server.com

# Verify key permissions
chmod 600 ~/.ssh/id_rsa
```

**Method unavailable:**
```bash
# Check available methods
python tunnel_tester.py --list-methods

# Install missing dependencies
pip install websocket-client dnspython
```

For detailed troubleshooting, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Legal & Ethical Use

⚠️ **Important:** This tool is for **educational and legitimate purposes only**.

- Only use on networks and systems you own or have explicit permission to test
- Using this tool may violate your carrier's Terms of Service
- Bypassing network restrictions may be illegal in some jurisdictions
- The authors are not responsible for any misuse

Read the full legal guidelines at [docs/LEGAL.md](docs/LEGAL.md).

## Contributing

Contributions are welcome! Here's how you can help:

### Adding New Methods

1. Create a new file in `python/methods/`
2. Implement the standard interface:
   ```python
   class NewMethod:
       METHOD_NAME = "new_method"
       DESCRIPTION = "Description of method"
       
       def test_connection(self, host, port, username, password, ...):
           # Return dict with status, latency, error, details
           
       def connect(self, host, port, username, password, ...):
           # Return True if connected
   ```
3. Register in `python/methods/__init__.py`
4. Add to `python/core.py` METHOD_CLASSES

### Code Style

- Follow PEP 8 for Python
- Use meaningful variable names
- Add docstrings to functions
- Include type hints where helpful

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Project Structure

```
ssh-tunnel-auto-tester/
├── README.md                 # This file
├── LICENSE                   # MIT License
├── requirements.txt          # Python dependencies
├── config.yaml.example       # Configuration template
├── .gitignore               # Git ignore rules
├── tunnel_tester.py         # Main CLI entry point
├── Dockerfile               # Docker container
├── docker-compose.yml       # Docker Compose config
├── ssh-tunnel-tester.service # systemd service file
├── python/
│   ├── __init__.py
│   ├── core.py              # Main orchestrator
│   ├── methods/
│   │   ├── __init__.py
│   │   ├── direct_ssh.py
│   │   ├── websocket_tunnel.py
│   │   ├── ssl_wrapper.py
│   │   ├── http_tunnel.py
│   │   ├── dns_tunnel.py
│   │   ├── sni_spoof.py
│   │   └── obfuscation.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── config_parser.py
│       ├── network_detector.py
│       └── speed_test.py
├── bash/
│   ├── tunnel_tester.sh     # Bash version
│   └── methods/
│       ├── direct_ssh.sh
│       ├── ssl_wrapper.sh
│       └── http_tunnel.sh
└── docs/
    ├── INSTALLATION.md
    ├── CONFIGURATION.md
    ├── TROUBLESHOOTING.md
    └── LEGAL.md
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Paramiko](https://www.paramiko.org/) - SSH library for Python
- [websocket-client](https://github.com/websocket-client/websocket-client) - WebSocket library
- [dnspython](https://www.dnspython.org/) - DNS toolkit for Python
- All contributors and testers

---

**Disclaimer:** This tool is provided for educational purposes. Use responsibly and legally.