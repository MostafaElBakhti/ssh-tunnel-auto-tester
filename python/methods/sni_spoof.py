"""
SNI Spoofing Method

SNI (Server Name Indication) spoofing to bypass DPI restrictions.
"""

import socket
import ssl
import time
from typing import Any, Dict, List, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SNISpoof:
    """
    SNI Spoofing handler for SSH connections.

    This method uses Server Name Indication spoofing to make
    connections appear as if they're going to popular/allowed
    domains, bypassing Deep Packet Inspection (DPI).
    """

    METHOD_NAME = "sni_spoof"
    DESCRIPTION = "SNI spoofing with fake host headers"

    # Popular domains that are usually not blocked
    DEFAULT_SNI_DOMAINS = [
        "www.google.com",
        "www.facebook.com",
        "www.microsoft.com",
        "www.cloudflare.com",
        "www.akamai.com",
        "www.amazon.com",
        "www.apple.com",
        "www.netflix.com",
        "www.youtube.com",
        "www.twitter.com",
    ]

    def __init__(self, logger=None):
        """
        Initialize SNISpoof handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.ssl_socket = None
        self.ssh_client = None
        self.connected = False

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required. Install with: pip install paramiko")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="SNISpoof")

    def _create_sni_context(self, sni_hostname: str, verify: bool = False) -> ssl.SSLContext:
        """
        Create SSL context with specific SNI hostname.

        Args:
            sni_hostname: SNI hostname to send
            verify: Whether to verify certificate

        Returns:
            SSL context configured for SNI spoofing
        """
        context = ssl.create_default_context()

        # Don't verify - we're sending fake SNI
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Use modern TLS
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        sni_domains: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if SNI spoofing can bypass restrictions.

        Args:
            host: Target SSH server hostname or IP
            port: Target port (usually 443)
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            sni_domains: List of SNI domains to try

        Returns:
            Dictionary with test results
        """
        result = {
            "method": self.METHOD_NAME,
            "status": "failed",
            "host": host,
            "port": port,
            "latency_ms": None,
            "error": None,
            "details": "",
            "working_sni": None,
        }

        domains_to_test = sni_domains or self.DEFAULT_SNI_DOMAINS

        for sni_domain in domains_to_test:
            test_result = self._test_single_sni(host, port, sni_domain, timeout)

            if test_result["success"]:
                result["status"] = "success"
                result["latency_ms"] = test_result["latency_ms"]
                result["working_sni"] = sni_domain
                result["details"] = f"SNI '{sni_domain}' works, {test_result['latency_ms']:.0f}ms"
                self._log(f"SNI spoofing successful with: {sni_domain}", "success")
                return result

        # No SNI domain worked
        result["error"] = "All SNI domains failed"
        result["details"] = f"Tested {len(domains_to_test)} domains, none worked"
        self._log("All SNI domains failed", "error")

        return result

    def _test_single_sni(
        self,
        host: str,
        port: int,
        sni_domain: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Test a single SNI domain.

        Args:
            host: Target host
            port: Target port
            sni_domain: SNI domain to spoof
            timeout: Connection timeout

        Returns:
            Dictionary with test results
        """
        result = {
            "success": False,
            "latency_ms": None,
            "error": None,
        }

        start_time = time.time()

        try:
            self._log(f"Testing SNI: {sni_domain} -> {host}:{port}")

            # Create raw socket
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, port))

            # Create SSL context and wrap with spoofed SNI
            context = self._create_sni_context(sni_domain)
            ssl_socket = context.wrap_socket(
                raw_socket,
                server_hostname=sni_domain  # This is the SNI we send
            )

            latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(latency, 2)

            # Try to receive data
            ssl_socket.settimeout(3)
            try:
                data = ssl_socket.recv(256)
                if data.startswith(b"SSH-"):
                    result["success"] = True
                    self._log(f"SSH banner received with SNI: {sni_domain}")
                elif data:
                    # Got some response, connection works
                    result["success"] = True
                    self._log(f"Response received with SNI: {sni_domain}")
            except socket.timeout:
                # No immediate response, but SSL handshake succeeded
                result["success"] = True
                self._log(f"SSL handshake OK with SNI: {sni_domain}")

            ssl_socket.close()

        except ssl.SSLError as e:
            result["error"] = f"SSL error: {e}"
            self._log(f"SSL error with {sni_domain}: {e}")

        except socket.timeout:
            result["error"] = "Connection timeout"

        except socket.error as e:
            result["error"] = f"Socket error: {e}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def connect(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        sni_domain: Optional[str] = None,
        sni_domains: Optional[List[str]] = None,
        compression: bool = True,
        **kwargs
    ) -> bool:
        """
        Establish SSH connection with SNI spoofing.

        Args:
            host: Target SSH server hostname
            port: Target port
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            sni_domain: Specific SNI domain to use
            sni_domains: List of SNI domains to try
            compression: Enable SSH compression

        Returns:
            True if connection established
        """
        # Determine SNI domain to use
        working_sni = sni_domain

        if not working_sni:
            # Find a working SNI domain
            domains_to_test = sni_domains or self.DEFAULT_SNI_DOMAINS
            for domain in domains_to_test:
                test_result = self._test_single_sni(host, port, domain, timeout)
                if test_result["success"]:
                    working_sni = domain
                    break

        if not working_sni:
            self._log("No working SNI domain found", "error")
            return False

        try:
            self._log(f"Connecting with SNI: {working_sni}")

            # Create SSL connection with spoofed SNI
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, port))

            context = self._create_sni_context(working_sni)
            self.ssl_socket = context.wrap_socket(
                raw_socket,
                server_hostname=working_sni
            )

            self._log(f"SSL connection established with SNI: {working_sni}")

            # Create SSH connection over SSL
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            transport = paramiko.Transport(self.ssl_socket)
            transport.connect(
                username=username,
                password=password,
                pkey=paramiko.RSAKey.from_private_key_file(key_file) if key_file else None
            )

            self.ssh_client._transport = transport
            self.connected = True

            self._log(f"SSH connection established via SNI spoofing", "success")
            return True

        except Exception as e:
            self._log(f"Connection failed: {e}", "error")
            self.disconnect()
            return False

    def disconnect(self):
        """Close the connection."""
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None

        if self.ssl_socket:
            try:
                self.ssl_socket.close()
            except Exception:
                pass
            self.ssl_socket = None

        self.connected = False
        self._log("Disconnected")

    def is_connected(self) -> bool:
        """Check if connection is active."""
        if not self.ssl_socket or not self.connected:
            return False

        try:
            self.ssl_socket.getpeername()
            return True
        except Exception:
            self.connected = False
            return False

    def get_client(self):
        """Get the underlying SSH client."""
        return self.ssh_client

    def find_best_sni(
        self,
        host: str,
        port: int,
        domains: Optional[List[str]] = None,
        timeout: int = 5
    ) -> Optional[str]:
        """
        Find the best working SNI domain.

        Args:
            host: Target host
            port: Target port
            domains: List of domains to test
            timeout: Connection timeout

        Returns:
            Best working SNI domain or None
        """
        domains_to_test = domains or self.DEFAULT_SNI_DOMAINS
        best_domain = None
        best_latency = float("inf")

        for domain in domains_to_test:
            test_result = self._test_single_sni(host, port, domain, timeout)
            if test_result["success"]:
                if test_result["latency_ms"] < best_latency:
                    best_latency = test_result["latency_ms"]
                    best_domain = domain

        return best_domain

    @staticmethod
    def test_sni_filtering(host: str = "www.google.com", timeout: int = 5) -> Dict[str, Any]:
        """
        Test if network filters SNI.

        Args:
            host: Host to test against
            timeout: Connection timeout

        Returns:
            Dictionary with SNI filtering information
        """
        result = {
            "sni_filtering_detected": False,
            "real_sni_works": False,
            "fake_sni_works": False,
            "details": "",
        }

        # Test with real SNI
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, 443))

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            ssl_socket = context.wrap_socket(raw_socket, server_hostname=host)
            ssl_socket.close()
            result["real_sni_works"] = True
        except Exception:
            pass

        # Test with fake SNI
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, 443))

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            ssl_socket = context.wrap_socket(raw_socket, server_hostname="www.example.com")
            ssl_socket.close()
            result["fake_sni_works"] = True
        except Exception:
            pass

        # Analyze results
        if result["real_sni_works"] and not result["fake_sni_works"]:
            result["sni_filtering_detected"] = True
            result["details"] = "Network filters based on SNI"
        elif result["real_sni_works"] and result["fake_sni_works"]:
            result["details"] = "No SNI filtering detected"
        elif not result["real_sni_works"]:
            result["details"] = "Cannot establish SSL connections"

        return result
