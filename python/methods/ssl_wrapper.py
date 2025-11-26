"""
SSL/TLS Wrapper Method

SSH wrapped in SSL/TLS (stunnel-like) for bypassing network restrictions.
"""

import socket
import ssl
import threading
import time
from typing import Any, Dict, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class SSLWrapper:
    """
    SSL/TLS wrapper for SSH connections.

    This method wraps SSH traffic in SSL/TLS, making it appear as
    regular HTTPS traffic to network filters.
    """

    METHOD_NAME = "ssl_wrap"
    DESCRIPTION = "SSH wrapped in SSL/TLS (stunnel-like)"

    def __init__(self, logger=None):
        """
        Initialize SSLWrapper handler.

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
            getattr(self.logger, level, self.logger.debug)(message, prefix="SSLWrapper")

    def _create_ssl_context(self, verify: bool = False) -> ssl.SSLContext:
        """
        Create SSL context for connection.

        Args:
            verify: Whether to verify server certificate

        Returns:
            SSL context
        """
        context = ssl.create_default_context()

        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        # Set modern cipher suites
        context.set_ciphers("HIGH:!aNULL:!MD5:!RC4")

        return context

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        ssl_verify: bool = False,
        sni_hostname: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if SSL-wrapped SSH connection is possible.

        Args:
            host: Server hostname or IP
            port: Server port (usually 443)
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            ssl_verify: Verify SSL certificate
            sni_hostname: SNI hostname to use

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
        }

        start_time = time.time()

        try:
            self._log(f"Testing SSL connection to {host}:{port}")

            # Create SSL context
            ssl_context = self._create_ssl_context(verify=ssl_verify)

            # Create raw socket
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, port))

            # Wrap in SSL
            server_hostname = sni_hostname or host
            ssl_socket = ssl_context.wrap_socket(
                raw_socket,
                server_hostname=server_hostname
            )

            ssl_latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(ssl_latency, 2)

            # Get SSL info
            ssl_info = ssl_socket.cipher()
            ssl_version = ssl_socket.version()

            self._log(f"SSL handshake successful: {ssl_version}, {ssl_info[0]}")

            # Test if this is an SSH-over-SSL endpoint
            # Try to receive SSH banner
            ssl_socket.settimeout(3)
            try:
                banner = ssl_socket.recv(256)
                if banner.startswith(b"SSH-"):
                    result["status"] = "success"
                    result["details"] = f"SSL+SSH in {ssl_latency:.0f}ms ({ssl_version})"
                    self._log("SSH banner received through SSL", "success")
                else:
                    # SSL works, but not SSH behind it
                    result["status"] = "success"
                    result["details"] = f"SSL connected (no SSH banner), {ssl_latency:.0f}ms"
                    self._log("SSL connected, no SSH banner (may need SSL tunnel server)")
            except socket.timeout:
                # No banner, but SSL works
                result["status"] = "success"
                result["details"] = f"SSL connected in {ssl_latency:.0f}ms"
                self._log("SSL connected (no immediate response)")

            ssl_socket.close()

        except ssl.SSLError as e:
            result["error"] = f"SSL error: {e}"
            result["details"] = "SSL/TLS handshake failed"
            self._log(f"SSL error: {e}", "error")

        except socket.timeout:
            result["error"] = "Connection timed out"
            result["details"] = f"Timeout after {timeout}s"
            self._log(f"Connection timeout", "error")

        except socket.error as e:
            result["error"] = f"Socket error: {e}"
            result["details"] = "Network unreachable or port blocked"
            self._log(f"Socket error: {e}", "error")

        except Exception as e:
            result["error"] = f"Error: {type(e).__name__}"
            result["details"] = str(e)
            self._log(f"Unexpected error: {e}", "error")

        return result

    def connect(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        ssl_verify: bool = False,
        sni_hostname: Optional[str] = None,
        compression: bool = True,
        **kwargs
    ) -> bool:
        """
        Establish SSL-wrapped SSH connection.

        Note: This requires an SSL-to-SSH tunnel server (like stunnel) on
        the server side, or an SSH server configured to accept SSL-wrapped
        connections.

        Args:
            host: Server hostname
            port: Server port (usually 443)
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            ssl_verify: Verify SSL certificate
            sni_hostname: SNI hostname
            compression: Enable SSH compression

        Returns:
            True if connection established
        """
        try:
            self._log(f"Establishing SSL connection to {host}:{port}")

            # Create SSL context
            ssl_context = self._create_ssl_context(verify=ssl_verify)

            # Create raw socket
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, port))

            # Wrap in SSL
            server_hostname = sni_hostname or host
            self.ssl_socket = ssl_context.wrap_socket(
                raw_socket,
                server_hostname=server_hostname
            )

            self._log("SSL tunnel established")

            # Create Paramiko SSH client over SSL socket
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Create transport over SSL socket
            transport = paramiko.Transport(self.ssl_socket)
            transport.connect(
                username=username,
                password=password,
                pkey=paramiko.RSAKey.from_private_key_file(key_file) if key_file else None
            )

            self.ssh_client._transport = transport
            self.connected = True

            self._log(f"SSL-wrapped SSH connection established", "success")
            return True

        except Exception as e:
            self._log(f"Connection failed: {e}", "error")
            self.disconnect()
            return False

    def disconnect(self):
        """Close the SSL-wrapped connection."""
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
            # Check SSL socket
            self.ssl_socket.getpeername()
            return True
        except Exception:
            self.connected = False
            return False

    def get_client(self):
        """Get the underlying SSH client."""
        return self.ssh_client

    @staticmethod
    def test_ssl_port(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """
        Test if a port accepts SSL connections and get certificate info.

        Args:
            host: Target host
            port: Target port
            timeout: Connection timeout

        Returns:
            Dictionary with SSL information
        """
        result = {
            "success": False,
            "ssl_version": None,
            "cipher": None,
            "cert_subject": None,
            "cert_issuer": None,
            "error": None,
        }

        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(timeout)
            raw_socket.connect((host, port))

            ssl_socket = context.wrap_socket(raw_socket, server_hostname=host)

            result["success"] = True
            result["ssl_version"] = ssl_socket.version()
            result["cipher"] = ssl_socket.cipher()

            try:
                cert = ssl_socket.getpeercert()
                if cert:
                    result["cert_subject"] = dict(x[0] for x in cert.get("subject", []))
                    result["cert_issuer"] = dict(x[0] for x in cert.get("issuer", []))
            except Exception:
                pass

            ssl_socket.close()

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def find_ssl_ports(host: str, ports: list, timeout: int = 2) -> list:
        """
        Find ports that accept SSL connections.

        Args:
            host: Target host
            ports: List of ports to test
            timeout: Connection timeout per port

        Returns:
            List of ports that accept SSL
        """
        ssl_ports = []

        for port in ports:
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw_socket.settimeout(timeout)
                raw_socket.connect((host, port))

                ssl_socket = context.wrap_socket(raw_socket, server_hostname=host)
                ssl_socket.close()
                ssl_ports.append(port)

            except Exception:
                continue

        return ssl_ports
