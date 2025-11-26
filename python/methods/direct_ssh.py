"""
Direct SSH Connection Method

Standard SSH connection without any tunneling or obfuscation.
"""

import socket
import time
from typing import Any, Dict, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class DirectSSH:
    """
    Direct SSH connection handler.

    This is the simplest connection method - standard SSH connection
    to the specified host and port.
    """

    METHOD_NAME = "direct"
    DESCRIPTION = "Direct SSH connection (standard)"

    def __init__(self, logger=None):
        """
        Initialize DirectSSH handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.client = None
        self.connected = False

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required for SSH connections. Install with: pip install paramiko")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="DirectSSH")

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if direct SSH connection is possible.

        Args:
            host: SSH server hostname or IP
            port: SSH server port
            username: SSH username
            password: SSH password (optional if using key)
            key_file: Path to private key file (optional)
            timeout: Connection timeout in seconds

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
            # First, test raw socket connection
            self._log(f"Testing socket connection to {host}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            socket_latency = (time.time() - start_time) * 1000
            sock.close()

            self._log(f"Socket connection successful (latency: {socket_latency:.2f}ms)")

            # Now test SSH connection
            start_time = time.time()
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "banner_timeout": timeout,
                "auth_timeout": timeout,
            }

            if key_file:
                self._log(f"Using key file: {key_file}")
                connect_kwargs["key_filename"] = key_file
            elif password:
                connect_kwargs["password"] = password
            else:
                result["error"] = "No authentication method provided"
                result["details"] = "Must provide either password or key_file"
                return result

            client.connect(**connect_kwargs)

            ssh_latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(ssh_latency, 2)

            # Verify connection with a simple command
            stdin, stdout, stderr = client.exec_command("echo connected", timeout=timeout)
            output = stdout.read().decode().strip()

            if output == "connected":
                result["status"] = "success"
                result["details"] = f"Connected in {ssh_latency:.0f}ms"
                self._log(f"SSH connection successful to {host}:{port}", "success")
            else:
                result["error"] = "Connection verification failed"
                result["details"] = "Could not verify SSH connection"

            client.close()

        except socket.timeout:
            result["error"] = "Connection timed out"
            result["details"] = f"Timeout after {timeout}s"
            self._log(f"Connection timeout to {host}:{port}", "error")

        except socket.error as e:
            result["error"] = f"Socket error: {e}"
            result["details"] = "Network unreachable or port blocked"
            self._log(f"Socket error: {e}", "error")

        except paramiko.AuthenticationException as e:
            result["error"] = "Authentication failed"
            result["details"] = str(e)
            self._log(f"Authentication failed: {e}", "error")

        except paramiko.SSHException as e:
            result["error"] = f"SSH error: {e}"
            result["details"] = str(e)
            self._log(f"SSH error: {e}", "error")

        except Exception as e:
            result["error"] = f"Unexpected error: {type(e).__name__}"
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
        compression: bool = True,
        **kwargs
    ) -> bool:
        """
        Establish and maintain SSH connection.

        Args:
            host: SSH server hostname or IP
            port: SSH server port
            username: SSH username
            password: SSH password (optional if using key)
            key_file: Path to private key file (optional)
            timeout: Connection timeout in seconds
            compression: Enable SSH compression

        Returns:
            True if connection established successfully
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "banner_timeout": timeout,
                "auth_timeout": timeout,
                "compress": compression,
            }

            if key_file:
                connect_kwargs["key_filename"] = key_file
            elif password:
                connect_kwargs["password"] = password
            else:
                self._log("No authentication method provided", "error")
                return False

            self._log(f"Connecting to {host}:{port}...")
            self.client.connect(**connect_kwargs)
            self.connected = True
            self._log(f"Connected to {host}:{port}", "success")
            return True

        except Exception as e:
            self._log(f"Connection failed: {e}", "error")
            self.connected = False
            return False

    def disconnect(self):
        """Close the SSH connection."""
        if self.client:
            try:
                self.client.close()
                self._log("Disconnected")
            except Exception:
                pass
            finally:
                self.client = None
                self.connected = False

    def is_connected(self) -> bool:
        """Check if connection is still active."""
        if not self.client or not self.connected:
            return False

        try:
            # Send a keep-alive to check connection
            transport = self.client.get_transport()
            if transport and transport.is_active():
                return True
        except Exception:
            pass

        self.connected = False
        return False

    def get_client(self):
        """Get the underlying Paramiko SSH client."""
        return self.client

    def execute_command(self, command: str, timeout: int = 30) -> tuple:
        """
        Execute a command on the remote server.

        Args:
            command: Command to execute
            timeout: Command timeout

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to SSH server")

        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()

        return (
            stdout.read().decode("utf-8"),
            stderr.read().decode("utf-8"),
            exit_code
        )

    def create_tunnel(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int
    ):
        """
        Create an SSH port forwarding tunnel.

        Args:
            local_port: Local port to bind
            remote_host: Remote host to forward to
            remote_port: Remote port to forward to

        Returns:
            Tunnel object
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to SSH server")

        transport = self.client.get_transport()
        return transport.request_port_forward("", local_port)

    @staticmethod
    def scan_ports(host: str, ports: list, timeout: int = 2) -> Dict[int, bool]:
        """
        Scan multiple ports for accessibility.

        Args:
            host: Target host
            ports: List of ports to scan
            timeout: Connection timeout per port

        Returns:
            Dictionary mapping port to accessibility status
        """
        results = {}

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                results[port] = (result == 0)
                sock.close()
            except Exception:
                results[port] = False

        return results
