# Troubleshooting Guide

This guide helps you diagnose and fix common issues with SSH Tunnel Auto-Tester.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Connection Issues](#connection-issues)
- [Authentication Errors](#authentication-errors)
- [Method-Specific Issues](#method-specific-issues)
- [Network Detection Issues](#network-detection-issues)
- [Performance Issues](#performance-issues)
- [Installation Issues](#installation-issues)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

## Quick Diagnostics

Run these commands to quickly diagnose issues:

```bash
# Check available methods
python tunnel_tester.py --list-methods

# Detect network
python tunnel_tester.py --detect-network

# Verbose test
python tunnel_tester.py --auto --verbose

# Check configuration
python tunnel_tester.py --config config.yaml --list-methods
```

## Connection Issues

### No Methods Working

**Symptoms:** All connection methods fail.

**Possible Causes:**
1. Target server is down
2. Network blocks all outgoing connections
3. Firewall rules preventing connections

**Solutions:**

1. Verify server is reachable:
   ```bash
   ping your-server.com
   nc -zv your-server.com 22
   ```

2. Check basic connectivity:
   ```bash
   curl -I https://google.com
   ```

3. Try different ports:
   ```bash
   python tunnel_tester.py --ports 80,443,8080 --auto
   ```

### Timeout Errors

**Symptoms:** "Connection timed out" errors.

**Solutions:**

1. Increase timeout:
   ```yaml
   # In config.yaml
   timeout: 30
   ```

2. Or via command line:
   ```bash
   python tunnel_tester.py --auto --timeout 30
   ```

3. Check if network is slow:
   ```bash
   python tunnel_tester.py --detect-network
   ```

### Connection Reset

**Symptoms:** "Connection reset by peer" errors.

**Possible Causes:**
- Deep Packet Inspection (DPI) blocking SSH
- Firewall terminating connections

**Solutions:**

1. Try SSL-wrapped methods:
   ```bash
   python tunnel_tester.py --method ssl_wrap --auto
   ```

2. Try SNI spoofing:
   ```bash
   python tunnel_tester.py --method sni_spoof --auto
   ```

3. Use port 443 (HTTPS):
   ```bash
   python tunnel_tester.py --port 443 --auto
   ```

## Authentication Errors

### "Authentication Failed"

**Symptoms:** SSH connection establishes but authentication fails.

**Solutions:**

1. Verify credentials:
   ```bash
   # Test direct SSH
   ssh -v user@your-server.com
   ```

2. Check username/password in config
3. Try key-based authentication:
   ```yaml
   ssh_accounts:
     - host: "server.com"
       username: "user"
       key_file: "~/.ssh/id_rsa"
       password: null
   ```

### Key File Issues

**Symptoms:** "Permission denied" with key file.

**Solutions:**

1. Check key file permissions:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

2. Verify key file path:
   ```bash
   ls -la ~/.ssh/id_rsa
   ```

3. Test key manually:
   ```bash
   ssh -i ~/.ssh/id_rsa user@server.com
   ```

### "Permission Denied (publickey)"

**Solutions:**

1. Add key to ssh-agent:
   ```bash
   eval $(ssh-agent)
   ssh-add ~/.ssh/id_rsa
   ```

2. Check server's authorized_keys

3. Try password authentication instead

## Method-Specific Issues

### Direct SSH Fails

**Symptoms:** Direct method fails but network works.

**Solutions:**

1. Verify SSH port is correct
2. Check if SSH is blocked:
   ```bash
   nc -zv server.com 22
   ```
3. Try different ports

### WebSocket Tunnel Issues

**Symptoms:** WebSocket method fails.

**Possible Causes:**
- Server doesn't have WebSocket proxy
- WebSocket blocked by network

**Solutions:**

1. Verify websocket-client is installed:
   ```bash
   pip install websocket-client
   ```

2. Test WebSocket connectivity:
   ```python
   import websocket
   ws = websocket.create_connection("wss://server:443/ws")
   ```

3. Check if server has WebSocket endpoint

### SSL Wrapper Issues

**Symptoms:** SSL wrap method fails.

**Solutions:**

1. Test SSL connectivity:
   ```bash
   openssl s_client -connect server.com:443
   ```

2. Check if server accepts SSL connections on target port

3. For Bash version, install stunnel:
   ```bash
   sudo apt-get install stunnel4
   ```

### HTTP Tunnel Issues

**Symptoms:** HTTP CONNECT fails.

**Solutions:**

1. Verify proxy settings
2. Test HTTP CONNECT manually:
   ```bash
   echo -e "CONNECT server.com:22 HTTP/1.1\r\nHost: server.com:22\r\n\r\n" | nc proxy 8080
   ```

3. Check for proxy authentication requirements

### SNI Spoofing Issues

**Symptoms:** SNI method fails.

**Solutions:**

1. Try different SNI domains:
   ```yaml
   sni_domains:
     - "www.google.com"
     - "www.amazon.com"
     - "www.microsoft.com"
   ```

2. Check if DPI inspects SNI
3. Use port 443 for best results

### DNS Tunnel Issues

**Symptoms:** DNS tunnel method fails.

**Solutions:**

1. Verify dnspython is installed:
   ```bash
   pip install dnspython
   ```

2. Test DNS connectivity:
   ```bash
   nslookup google.com
   ```

3. Note: DNS tunneling requires server-side setup (e.g., iodine)

## Network Detection Issues

### Wrong Network Type Detected

**Symptoms:** Tool incorrectly identifies network type.

**Solutions:**

1. Run manual detection:
   ```bash
   python tunnel_tester.py --detect-network --verbose
   ```

2. Check network interface:
   ```bash
   ip addr
   # or
   ifconfig
   ```

3. Disable auto-adaptation:
   ```yaml
   network_detection:
     enabled: false
   ```

### No Internet Detected

**Symptoms:** Tool reports no internet but you have connectivity.

**Solutions:**

1. Check DNS resolution:
   ```bash
   nslookup google.com
   ```

2. Test connectivity:
   ```bash
   ping 8.8.8.8
   curl https://api.ipify.org
   ```

3. Check if test hosts are blocked

## Performance Issues

### Slow Testing

**Symptoms:** Tests take very long.

**Solutions:**

1. Reduce timeout:
   ```yaml
   timeout: 5
   ```

2. Enable parallel testing (default):
   ```yaml
   max_threads: 5
   ```

3. Test fewer ports/methods

### High CPU Usage

**Solutions:**

1. Reduce concurrent threads:
   ```yaml
   max_threads: 2
   ```

2. Add delay between tests:
   ```yaml
   connection_delay: 2
   ```

### Connection Dropping

**Symptoms:** Connection established but drops frequently.

**Solutions:**

1. Enable keep-alive:
   ```yaml
   keep_alive: true
   keep_alive_interval: 30
   ```

2. Enable auto-reconnect:
   ```yaml
   auto_reconnect: true
   max_reconnect_attempts: 10
   ```

## Installation Issues

### Missing Dependencies

**Symptoms:** Import errors or missing module errors.

**Solutions:**

1. Install all requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. For specific modules:
   ```bash
   pip install paramiko websocket-client dnspython
   ```

3. Check Python version:
   ```bash
   python --version
   # Should be 3.8+
   ```

### Colorama Not Working

**Symptoms:** No colored output on Windows.

**Solutions:**

```bash
pip install colorama
```

For Windows:
```python
from colorama import init
init()
```

### Permission Errors on Linux

**Symptoms:** Permission denied errors.

**Solutions:**

1. Run with sudo (if needed):
   ```bash
   sudo python tunnel_tester.py --auto
   ```

2. Or fix permissions:
   ```bash
   chmod +x tunnel_tester.py
   ```

## Debug Mode

### Enable Verbose Logging

```bash
python tunnel_tester.py --auto --verbose
```

### Check Log File

```bash
cat tunnel_results.log
```

### Debug Configuration

```yaml
log_level: "DEBUG"
verbose: true
```

### Python Debug

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Network Debug

```bash
# Check open ports on server
nc -zv server.com 22 80 443 8080

# Check routing
traceroute server.com

# Check DNS
nslookup server.com

# Check SSL
openssl s_client -connect server.com:443 -servername server.com
```

## Common Error Messages

### "No SSH accounts configured"

Add accounts to config.yaml or use command line:
```bash
python tunnel_tester.py --host server.com --user myuser
```

### "Method not available"

Install missing dependencies:
```bash
python tunnel_tester.py --list-methods
pip install <missing-package>
```

### "Circuit breaker open"

Wait for the pause duration or disable:
```yaml
circuit_breaker:
  enabled: false
```

### "Invalid YAML"

Check config.yaml syntax:
```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

## Getting Help

If you can't resolve your issue:

1. **Check existing issues:**
   https://github.com/your-repo/ssh-tunnel-auto-tester/issues

2. **Create a new issue with:**
   - OS and Python version
   - Full error message
   - Config (with passwords removed)
   - Output of `--verbose` mode

3. **Include debug information:**
   ```bash
   python --version
   pip list
   python tunnel_tester.py --list-methods
   python tunnel_tester.py --detect-network
   ```

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Timeout | Increase `timeout` in config |
| All methods fail | Check server/network connectivity |
| Auth failed | Verify credentials |
| Method unavailable | Install dependencies |
| Slow performance | Reduce `max_threads` |
| Connection drops | Enable `keep_alive` |
| No colored output | Install `colorama` |
