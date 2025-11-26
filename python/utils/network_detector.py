"""
Network Detector Module - Detect network type and conditions
"""

import os
import platform
import re
import socket
import subprocess
from typing import Dict, Optional, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class NetworkDetector:
    """
    Detect network type, carrier information, and connection status.
    """

    # Common mobile network interface patterns
    MOBILE_INTERFACE_PATTERNS = [
        r"wwan\d*",      # Linux WWAN interfaces
        r"usb\d*",       # USB tethering
        r"rmnet\d*",     # Qualcomm modems
        r"pdp\d*",       # Android data interfaces
        r"ccmni\d*",     # MediaTek modems
        r"cellular\d*",  # Generic cellular
    ]

    # Common carrier identifiers (partial)
    KNOWN_CARRIERS = {
        "T-Mobile": ["t-mobile", "tmobile"],
        "AT&T": ["att", "at&t", "cingular"],
        "Verizon": ["verizon", "vzw"],
        "Sprint": ["sprint"],
        "Vodafone": ["vodafone"],
        "Orange": ["orange"],
        "O2": ["o2"],
        "Three": ["three", "3uk"],
    }

    def __init__(self, logger=None):
        """
        Initialize network detector.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.system = platform.system().lower()

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message)

    def detect_network_type(self) -> Dict[str, any]:
        """
        Detect the current network type and details.

        Returns:
            Dictionary with network information
        """
        result = {
            "type": "unknown",
            "is_mobile": False,
            "is_wifi": False,
            "is_ethernet": False,
            "interface": None,
            "carrier": None,
            "signal_strength": None,
            "ip_address": None,
            "gateway": None,
        }

        # Try to detect using psutil
        if PSUTIL_AVAILABLE:
            result.update(self._detect_with_psutil())

        # Try platform-specific detection
        if self.system == "linux":
            result.update(self._detect_linux())
        elif self.system == "darwin":
            result.update(self._detect_macos())
        elif self.system == "windows":
            result.update(self._detect_windows())

        # Determine network type
        if result["is_mobile"]:
            result["type"] = "mobile"
        elif result["is_wifi"]:
            result["type"] = "wifi"
        elif result["is_ethernet"]:
            result["type"] = "ethernet"

        return result

    def _detect_with_psutil(self) -> Dict:
        """Detect network using psutil library."""
        result = {}

        try:
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, addrs in interfaces.items():
                # Skip loopback
                if iface_name.lower() in ["lo", "loopback"]:
                    continue

                # Check if interface is up
                if iface_name in stats and stats[iface_name].isup:
                    # Get IPv4 address
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            result["ip_address"] = addr.address
                            result["interface"] = iface_name

                            # Check interface type
                            iface_lower = iface_name.lower()
                            if any(re.match(p, iface_lower) for p in self.MOBILE_INTERFACE_PATTERNS):
                                result["is_mobile"] = True
                            elif "wl" in iface_lower or "wifi" in iface_lower or "wlan" in iface_lower:
                                result["is_wifi"] = True
                            elif "eth" in iface_lower or "en" in iface_lower:
                                result["is_ethernet"] = True
                            break
        except Exception as e:
            self._log(f"psutil detection error: {e}", "debug")

        return result

    def _detect_linux(self) -> Dict:
        """Linux-specific network detection."""
        result = {}

        try:
            # Try to get default route interface
            route_output = subprocess.run(
                ["ip", "route", "get", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if route_output.returncode == 0:
                match = re.search(r"dev\s+(\S+)", route_output.stdout)
                if match:
                    iface = match.group(1)
                    result["interface"] = iface

                    # Check if mobile
                    if any(re.match(p, iface) for p in self.MOBILE_INTERFACE_PATTERNS):
                        result["is_mobile"] = True

                # Get gateway
                gw_match = re.search(r"via\s+(\S+)", route_output.stdout)
                if gw_match:
                    result["gateway"] = gw_match.group(1)

            # Try to detect carrier from NetworkManager
            nm_output = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,CONNECTION,DEVICE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if nm_output.returncode == 0:
                for line in nm_output.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        conn_type = parts[0].lower()
                        if "gsm" in conn_type or "cdma" in conn_type or "mobile" in conn_type:
                            result["is_mobile"] = True
                        elif "wireless" in conn_type or "wifi" in conn_type:
                            result["is_wifi"] = True
                        elif "ethernet" in conn_type:
                            result["is_ethernet"] = True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self._log(f"Linux detection error: {e}", "debug")

        return result

    def _detect_macos(self) -> Dict:
        """macOS-specific network detection."""
        result = {}

        try:
            # Get network service info
            output = subprocess.run(
                ["networksetup", "-listallhardwareports"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if output.returncode == 0:
                if "Wi-Fi" in output.stdout:
                    result["is_wifi"] = True
                if "Ethernet" in output.stdout:
                    result["is_ethernet"] = True
                if "iPhone USB" in output.stdout or "USB" in output.stdout:
                    result["is_mobile"] = True  # Possible tethering

            # Get default route
            route_output = subprocess.run(
                ["route", "-n", "get", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if route_output.returncode == 0:
                match = re.search(r"interface:\s+(\S+)", route_output.stdout)
                if match:
                    result["interface"] = match.group(1)

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self._log(f"macOS detection error: {e}", "debug")

        return result

    def _detect_windows(self) -> Dict:
        """Windows-specific network detection."""
        result = {}

        try:
            # Get network adapter info using netsh
            output = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if output.returncode == 0:
                if "Wi-Fi" in output.stdout or "Wireless" in output.stdout:
                    result["is_wifi"] = True
                if "Ethernet" in output.stdout:
                    result["is_ethernet"] = True
                if "Mobile" in output.stdout or "Cellular" in output.stdout:
                    result["is_mobile"] = True

            # Get IP configuration
            ipconfig = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if ipconfig.returncode == 0:
                # Find IPv4 address
                match = re.search(r"IPv4 Address.*?:\s*(\d+\.\d+\.\d+\.\d+)", ipconfig.stdout)
                if match:
                    result["ip_address"] = match.group(1)

                # Find gateway
                gw_match = re.search(r"Default Gateway.*?:\s*(\d+\.\d+\.\d+\.\d+)", ipconfig.stdout)
                if gw_match:
                    result["gateway"] = gw_match.group(1)

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self._log(f"Windows detection error: {e}", "debug")

        return result

    def check_internet_connectivity(self, timeout: int = 5) -> Tuple[bool, float]:
        """
        Check if internet is accessible.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            Tuple of (is_connected, latency_ms)
        """
        test_hosts = [
            ("8.8.8.8", 53),        # Google DNS
            ("1.1.1.1", 53),        # Cloudflare DNS
            ("208.67.222.222", 53), # OpenDNS
        ]

        import time

        for host, port in test_hosts:
            try:
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                latency = (time.time() - start_time) * 1000
                sock.close()
                return True, latency
            except (socket.timeout, socket.error, OSError):
                continue

        return False, 0.0

    def get_public_ip(self, timeout: int = 5) -> Optional[str]:
        """
        Get public IP address.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Public IP address or None
        """
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.ipify.org",
                headers={"User-Agent": "SSH-Tunnel-Tester/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8").strip()
        except Exception:
            pass

        try:
            import urllib.request
            req = urllib.request.Request(
                "https://icanhazip.com",
                headers={"User-Agent": "SSH-Tunnel-Tester/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8").strip()
        except Exception:
            return None

    def suggest_strategy(self, network_info: Dict) -> list:
        """
        Suggest optimal testing strategy based on network type.

        Args:
            network_info: Network information dictionary

        Returns:
            List of recommended test modes in priority order
        """
        if network_info.get("is_mobile"):
            # Mobile networks often have more restrictions
            return [
                "ssl_wrap",      # SSL often unrestricted
                "websocket",     # WebSocket usually works
                "http_tunnel",   # HTTP CONNECT may work
                "sni_spoof",     # SNI spoofing for DPI bypass
                "direct",        # Try direct as fallback
            ]
        elif network_info.get("is_wifi"):
            # WiFi networks vary widely
            return [
                "direct",        # Try direct first
                "ssl_wrap",      # SSL wrapper
                "websocket",     # WebSocket
                "http_tunnel",   # HTTP tunnel
                "sni_spoof",     # SNI spoof
            ]
        else:
            # Ethernet - typically least restricted
            return [
                "direct",
                "ssl_wrap",
                "websocket",
                "http_tunnel",
            ]
