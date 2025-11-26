"""
Configuration Parser Module - YAML configuration handling for SSH Tunnel Tester
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ConfigError(Exception):
    """Configuration related errors."""
    pass


class ConfigParser:
    """
    Parser for YAML configuration files with validation and defaults.
    """

    # Default configuration values
    DEFAULTS = {
        "ssh_accounts": [],
        "test_modes": ["direct", "websocket", "ssl_wrap", "http_tunnel", "sni_spoof"],
        "ports_to_test": [22, 80, 443, 8080, 8443],
        "sni_domains": [
            "www.google.com",
            "www.facebook.com",
            "www.microsoft.com",
            "www.cloudflare.com",
        ],
        "timeout": 10,
        "retry_attempts": 3,
        "max_threads": 5,
        "connection_delay": 1,
        "log_file": "tunnel_results.log",
        "log_level": "INFO",
        "verbose": False,
        "quiet": False,
        "colorize": True,
        "auto_connect": True,
        "keep_alive": True,
        "keep_alive_interval": 60,
        "auto_reconnect": True,
        "max_reconnect_attempts": 5,
        "compression": True,
        "tcp_nodelay": True,
        "proxy": {
            "enabled": False,
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": None,
            "password": None,
        },
        "circuit_breaker": {
            "enabled": True,
            "failure_threshold": 5,
            "pause_duration": 30,
        },
        "cache": {
            "enabled": True,
            "file": ".cache.json",
            "max_age": 86400,
        },
        "network_detection": {
            "enabled": True,
            "detect_mobile": True,
            "adapt_strategy": True,
        },
        "speed_test": {
            "enabled": True,
            "test_size": 10240,
            "min_speed": 1024,
        },
        "export": {
            "format": "json",
            "file": "results.json",
            "include_timestamps": True,
            "include_metrics": True,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration parser.

        Args:
            config_path: Path to YAML configuration file
        """
        if not YAML_AVAILABLE:
            raise ConfigError("PyYAML is required. Install with: pip install pyyaml")

        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_defaults()

        if config_path:
            self.load(config_path)

    def _load_defaults(self):
        """Load default configuration values."""
        self.config = self._deep_copy(self.DEFAULTS)

    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of a dictionary or list."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge override dictionary into base dictionary."""
        result = self._deep_copy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = self._deep_copy(value)
        return result

    def load(self, config_path: str):
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Raises:
            ConfigError: If file cannot be read or parsed
        """
        path = Path(config_path)

        if not path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in configuration file: {e}")
        except IOError as e:
            raise ConfigError(f"Cannot read configuration file: {e}")

        # Merge user config with defaults
        self.config = self._deep_merge(self.DEFAULTS, user_config)
        self.config_path = config_path

        # Validate configuration
        self._validate()

    def _validate(self):
        """
        Validate configuration values.

        Raises:
            ConfigError: If configuration is invalid
        """
        # Validate SSH accounts
        accounts = self.config.get("ssh_accounts", [])
        if not isinstance(accounts, list):
            raise ConfigError("ssh_accounts must be a list")

        for i, account in enumerate(accounts):
            if not isinstance(account, dict):
                raise ConfigError(f"SSH account {i} must be a dictionary")
            if "host" not in account:
                raise ConfigError(f"SSH account {i} missing 'host' field")
            if "username" not in account:
                raise ConfigError(f"SSH account {i} missing 'username' field")
            if not account.get("password") and not account.get("key_file"):
                raise ConfigError(
                    f"SSH account {i} must have either 'password' or 'key_file'"
                )

        # Validate test modes
        valid_modes = ["direct", "websocket", "ssl_wrap", "http_tunnel", 
                       "dns_tunnel", "sni_spoof", "obfuscated"]
        test_modes = self.config.get("test_modes", [])
        for mode in test_modes:
            if mode not in valid_modes:
                raise ConfigError(f"Invalid test mode: {mode}. Valid modes: {valid_modes}")

        # Validate ports
        ports = self.config.get("ports_to_test", [])
        for port in ports:
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ConfigError(f"Invalid port number: {port}")

        # Validate timeout
        timeout = self.config.get("timeout", 10)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ConfigError("timeout must be a positive number")

        # Validate retry attempts
        retries = self.config.get("retry_attempts", 3)
        if not isinstance(retries, int) or retries < 0:
            raise ConfigError("retry_attempts must be a non-negative integer")

        # Validate max threads
        threads = self.config.get("max_threads", 5)
        if not isinstance(threads, int) or threads < 1:
            raise ConfigError("max_threads must be a positive integer")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_ssh_accounts(self) -> List[Dict[str, Any]]:
        """Get list of SSH accounts."""
        return self.config.get("ssh_accounts", [])

    def get_test_modes(self) -> List[str]:
        """Get list of test modes to use."""
        return self.config.get("test_modes", [])

    def get_ports(self) -> List[int]:
        """Get list of ports to test."""
        return self.config.get("ports_to_test", [])

    def get_sni_domains(self) -> List[str]:
        """Get list of SNI domains for spoofing."""
        return self.config.get("sni_domains", [])

    def is_auto_connect(self) -> bool:
        """Check if auto-connect is enabled."""
        return self.config.get("auto_connect", True)

    def is_keep_alive(self) -> bool:
        """Check if keep-alive is enabled."""
        return self.config.get("keep_alive", True)

    def get_timeout(self) -> int:
        """Get connection timeout."""
        return self.config.get("timeout", 10)

    def get_retry_attempts(self) -> int:
        """Get number of retry attempts."""
        return self.config.get("retry_attempts", 3)

    def get_max_threads(self) -> int:
        """Get maximum number of concurrent threads."""
        return self.config.get("max_threads", 5)

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._deep_copy(self.config)

    def save(self, path: Optional[str] = None):
        """
        Save configuration to YAML file.

        Args:
            path: Output path (uses original path if not specified)
        """
        save_path = path or self.config_path
        if not save_path:
            raise ConfigError("No save path specified")

        # Create a sanitized copy (remove sensitive data)
        safe_config = self._deep_copy(self.config)
        for account in safe_config.get("ssh_accounts", []):
            if "password" in account:
                account["password"] = "***REDACTED***"

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(safe_config, f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def create_example_config(path: str = "config.yaml.example"):
        """
        Create an example configuration file.

        Args:
            path: Output path for example config
        """
        example_config = """# SSH Tunnel Auto-Tester Configuration
# Copy this file to config.yaml and edit with your settings

ssh_accounts:
  - host: "your-ssh-server.com"
    port: 22
    username: "your_username"
    password: "your_password"
    key_file: null

test_modes:
  - direct
  - websocket
  - ssl_wrap
  - http_tunnel
  - sni_spoof

ports_to_test: [22, 80, 443, 8080, 8443]

sni_domains:
  - "www.google.com"
  - "www.facebook.com"
  - "www.microsoft.com"

timeout: 10
retry_attempts: 3
max_threads: 5
log_file: "tunnel_results.log"
auto_connect: true
keep_alive: true
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(example_config)
