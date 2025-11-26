# Configuration Guide

This guide explains all configuration options for SSH Tunnel Auto-Tester.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration File](#configuration-file)
- [SSH Accounts](#ssh-accounts)
- [Test Modes](#test-modes)
- [Port Configuration](#port-configuration)
- [SNI Domains](#sni-domains)
- [Connection Settings](#connection-settings)
- [Auto-Connect Settings](#auto-connect-settings)
- [Performance Tuning](#performance-tuning)
- [Proxy Settings](#proxy-settings)
- [Advanced Settings](#advanced-settings)
- [Security Best Practices](#security-best-practices)

## Quick Start

1. Copy the example configuration:
   ```bash
   cp config.yaml.example config.yaml
   ```

2. Edit with your SSH server details:
   ```bash
   nano config.yaml
   ```

3. Minimum required settings:
   ```yaml
   ssh_accounts:
     - host: "your-ssh-server.com"
       username: "your_username"
       password: "your_password"
   ```

4. Run the tester:
   ```bash
   python tunnel_tester.py --auto
   ```

## Configuration File

The configuration file uses YAML format. Create `config.yaml` in the project root directory.

### File Location

The tool searches for configuration in this order:
1. Path specified with `--config` argument
2. `config.yaml` in current directory
3. `config.yml` in current directory
4. Built-in defaults

### Security Warning

⚠️ **Never commit `config.yaml` with real credentials to version control!**

The `.gitignore` file excludes `config.yaml` by default.

## SSH Accounts

Configure one or more SSH accounts to test:

```yaml
ssh_accounts:
  # Primary account
  - host: "ssh.example.com"
    port: 22
    username: "myuser"
    password: "mypassword"
    key_file: null

  # Backup account with key authentication
  - host: "backup.example.com"
    port: 22
    username: "admin"
    password: null
    key_file: "/home/user/.ssh/id_rsa"

  # Account with non-standard port
  - host: "special.example.com"
    port: 2222
    username: "user"
    password: "pass123"
    key_file: null
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `host` | string | Yes | SSH server hostname or IP |
| `port` | integer | No | SSH port (default: 22) |
| `username` | string | Yes | SSH username |
| `password` | string | No* | SSH password |
| `key_file` | string | No* | Path to private key |

*Either `password` or `key_file` must be provided.

## Test Modes

Specify which tunneling methods to test:

```yaml
test_modes:
  - direct           # Standard SSH (fastest)
  - websocket        # SSH over WebSocket
  - ssl_wrap         # SSH in SSL/TLS wrapper
  - http_tunnel      # SSH through HTTP CONNECT
  - sni_spoof        # SNI spoofing
  - dns_tunnel       # DNS tunneling (advanced)
  - obfuscated       # Traffic obfuscation
```

### Method Descriptions

| Method | Description | Use Case |
|--------|-------------|----------|
| `direct` | Standard SSH connection | Unrestricted networks |
| `websocket` | SSH over WebSocket protocol | Firewalls allowing WS |
| `ssl_wrap` | SSH wrapped in SSL/TLS | HTTPS-only networks |
| `http_tunnel` | HTTP CONNECT method | Proxy-only networks |
| `sni_spoof` | SSL with fake SNI | DPI-filtered networks |
| `dns_tunnel` | DNS query tunneling | Very restrictive networks |
| `obfuscated` | Traffic obfuscation | Networks with DPI |

### Priority Order

Methods are tested in the order listed. Put most likely to succeed first:

```yaml
# For 4G/mobile networks (often have DPI):
test_modes:
  - ssl_wrap
  - sni_spoof
  - websocket
  - http_tunnel
  - direct
```

## Port Configuration

Specify ports to test for each method:

```yaml
ports_to_test:
  - 22     # Standard SSH
  - 80     # HTTP (often open)
  - 443    # HTTPS (usually open)
  - 8080   # Alternative HTTP
  - 8443   # Alternative HTTPS
  - 2082   # cPanel
  - 2083   # cPanel SSL
  - 2086   # WHM
  - 2087   # WHM SSL
  - 2095   # Webmail
  - 2096   # Webmail SSL
```

### Common Open Ports

| Port | Protocol | Notes |
|------|----------|-------|
| 80 | HTTP | Almost always open |
| 443 | HTTPS | Almost always open |
| 8080 | HTTP Alt | Often open |
| 8443 | HTTPS Alt | Often open |
| 53 | DNS | For DNS tunneling |

## SNI Domains

Domains to use for SNI spoofing:

```yaml
sni_domains:
  - "www.google.com"
  - "www.facebook.com"
  - "www.microsoft.com"
  - "www.cloudflare.com"
  - "www.akamai.com"
  - "www.amazon.com"
  - "www.apple.com"
  - "www.netflix.com"
```

### Choosing SNI Domains

Use domains that:
- Are popular and widely used
- Are unlikely to be blocked
- Use HTTPS (port 443)
- Are from different providers

## Connection Settings

Basic connection parameters:

```yaml
timeout: 10              # Connection timeout (seconds)
retry_attempts: 3        # Retries per method
max_threads: 5           # Concurrent tests
connection_delay: 1      # Delay between tests (seconds)
```

### Tuning for Different Networks

**Fast Network:**
```yaml
timeout: 5
max_threads: 10
connection_delay: 0.5
```

**Slow/Unstable Network:**
```yaml
timeout: 30
max_threads: 2
connection_delay: 2
retry_attempts: 5
```

## Auto-Connect Settings

Configure automatic connection behavior:

```yaml
auto_connect: true           # Connect when method found
keep_alive: true             # Send keep-alive packets
keep_alive_interval: 60      # Interval (seconds)
auto_reconnect: true         # Reconnect on disconnect
max_reconnect_attempts: 5    # Max reconnection tries
```

## Performance Tuning

Optimize SSH connection performance:

```yaml
compression: true            # Enable SSH compression
tcp_nodelay: true           # Disable Nagle's algorithm

preferred_ciphers:
  - "aes256-gcm@openssh.com"
  - "aes128-gcm@openssh.com"
  - "aes256-ctr"
  - "aes128-ctr"
```

### Speed vs Security Trade-off

**Fastest (less secure):**
```yaml
preferred_ciphers:
  - "aes128-ctr"
  - "arcfour"
compression: false
```

**Most Secure (slower):**
```yaml
preferred_ciphers:
  - "aes256-gcm@openssh.com"
  - "chacha20-poly1305@openssh.com"
compression: true
```

## Proxy Settings

Configure external proxy:

```yaml
proxy:
  enabled: false
  type: "socks5"        # socks4, socks5, http, https
  host: "127.0.0.1"
  port: 1080
  username: null        # Optional
  password: null        # Optional
```

### Proxy Types

| Type | Description | Typical Port |
|------|-------------|--------------|
| `socks4` | SOCKS v4 proxy | 1080 |
| `socks5` | SOCKS v5 proxy | 1080 |
| `http` | HTTP proxy | 8080, 3128 |
| `https` | HTTPS proxy | 8080 |

## Advanced Settings

### Circuit Breaker

Pause testing after consecutive failures:

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 5    # Failures before pause
  pause_duration: 30      # Pause (seconds)
```

### Caching

Cache successful methods:

```yaml
cache:
  enabled: true
  file: ".cache.json"
  max_age: 86400          # 24 hours
```

### Network Detection

Adapt to network type:

```yaml
network_detection:
  enabled: true
  detect_mobile: true
  adapt_strategy: true
```

### Speed Test

Verify connection quality:

```yaml
speed_test:
  enabled: true
  test_size: 10240        # Test data size (bytes)
  min_speed: 1024         # Minimum speed (B/s)
```

### Export Settings

Configure result export:

```yaml
export:
  format: "json"          # json or csv
  file: "results.json"
  include_timestamps: true
  include_metrics: true
```

## Security Best Practices

### 1. Protect Configuration File

```bash
# Set restrictive permissions
chmod 600 config.yaml

# Use environment variables for sensitive data
export SSH_PASSWORD="your_password"
```

### 2. Use Key Authentication

```yaml
ssh_accounts:
  - host: "server.com"
    username: "user"
    key_file: "~/.ssh/id_ed25519"
    password: null
```

### 3. Secure Key Files

```bash
chmod 600 ~/.ssh/id_rsa
```

### 4. Avoid Storing Passwords

Use SSH keys when possible, or prompt for password:

```bash
python tunnel_tester.py --host server.com --user myuser
# Password will be prompted
```

### 5. Encrypted Configuration (Advanced)

Store passwords encrypted (requires custom implementation):

```yaml
ssh_accounts:
  - host: "server.com"
    username: "user"
    password_encrypted: "base64_encrypted_password"
```

## Complete Example

Here's a complete configuration example:

```yaml
# SSH Tunnel Auto-Tester Configuration

ssh_accounts:
  - host: "my-server.com"
    port: 22
    username: "admin"
    password: "secure_password"
    key_file: null

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

sni_domains:
  - "www.google.com"
  - "www.cloudflare.com"

timeout: 10
retry_attempts: 3
max_threads: 5

auto_connect: true
keep_alive: true
keep_alive_interval: 60

compression: true
tcp_nodelay: true

circuit_breaker:
  enabled: true
  failure_threshold: 5
  pause_duration: 30

cache:
  enabled: true
  file: ".cache.json"
  max_age: 86400

log_file: "tunnel_results.log"
log_level: "INFO"
verbose: false
colorize: true
```

## Next Steps

- See [INSTALLATION.md](INSTALLATION.md) for setup instructions
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- See [LEGAL.md](LEGAL.md) for usage guidelines
