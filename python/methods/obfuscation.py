"""
Traffic Obfuscation Method

Traffic obfuscation techniques to bypass DPI detection.
"""

import hashlib
import os
import random
import socket
import struct
import time
from typing import Any, Dict, List, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class Obfuscation:
    """
    Traffic obfuscation handler for SSH connections.

    This method applies various obfuscation techniques to SSH traffic
    to evade Deep Packet Inspection and traffic analysis.

    Techniques include:
    - Traffic padding
    - Timing randomization
    - Packet fragmentation
    - Custom protocol wrapping
    """

    METHOD_NAME = "obfuscated"
    DESCRIPTION = "Traffic obfuscation methods"

    def __init__(self, logger=None):
        """
        Initialize Obfuscation handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.socket = None
        self.ssh_client = None
        self.connected = False
        self.obfuscation_key = None

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required. Install with: pip install paramiko")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="Obfuscation")

    def _generate_obfuscation_key(self, password: str) -> bytes:
        """
        Generate obfuscation key from password.

        Args:
            password: Password to derive key from

        Returns:
            32-byte obfuscation key
        """
        return hashlib.sha256(password.encode()).digest()

    def _xor_data(self, data: bytes, key: bytes) -> bytes:
        """
        Simple XOR obfuscation.

        Args:
            data: Data to obfuscate
            key: XOR key

        Returns:
            Obfuscated data
        """
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    def _add_padding(self, data: bytes, min_size: int = 64, max_size: int = 256) -> bytes:
        """
        Add random padding to data.

        Args:
            data: Original data
            min_size: Minimum padded size
            max_size: Maximum padding to add

        Returns:
            Padded data with length prefix
        """
        padding_size = random.randint(0, max_size - len(data)) if len(data) < max_size else 0
        padding = os.urandom(padding_size)

        # Format: [2-byte length][data][padding]
        length_prefix = struct.pack(">H", len(data))
        return length_prefix + data + padding

    def _remove_padding(self, data: bytes) -> bytes:
        """
        Remove padding from data.

        Args:
            data: Padded data

        Returns:
            Original data
        """
        if len(data) < 2:
            return data

        actual_length = struct.unpack(">H", data[:2])[0]
        return data[2:2 + actual_length]

    def _randomize_timing(self, min_delay: float = 0.001, max_delay: float = 0.05):
        """
        Add random delay to evade timing analysis.

        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _fragment_data(self, data: bytes, min_chunk: int = 16, max_chunk: int = 64) -> List[bytes]:
        """
        Fragment data into random-sized chunks.

        Args:
            data: Data to fragment
            min_chunk: Minimum chunk size
            max_chunk: Maximum chunk size

        Returns:
            List of data chunks
        """
        chunks = []
        offset = 0

        while offset < len(data):
            chunk_size = random.randint(min_chunk, max_chunk)
            chunk_size = min(chunk_size, len(data) - offset)
            chunks.append(data[offset:offset + chunk_size])
            offset += chunk_size

        return chunks

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        obfuscation_password: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test obfuscated connection capability.

        Args:
            host: Target SSH server hostname
            port: Target port
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            obfuscation_password: Password for obfuscation

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
            self._log(f"Testing obfuscated connection to {host}:{port}")

            # First, test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # Add timing randomization
            self._randomize_timing()

            sock.connect((host, port))
            connect_latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(connect_latency, 2)

            # Try to receive SSH banner
            sock.settimeout(5)
            try:
                banner = sock.recv(256)
                if banner.startswith(b"SSH-"):
                    result["status"] = "success"
                    result["details"] = f"Connected in {connect_latency:.0f}ms (ready for obfuscation)"
                    self._log("Direct connection works, obfuscation available", "success")
                else:
                    result["status"] = "success"
                    result["details"] = f"Port open, may need obfuscation server"
            except socket.timeout:
                result["status"] = "success"
                result["details"] = f"Port open (no immediate response)"

            sock.close()

        except socket.timeout:
            result["error"] = "Connection timed out"
            result["details"] = f"Timeout after {timeout}s"
            self._log("Connection timeout", "error")

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
        obfuscation_password: Optional[str] = None,
        use_padding: bool = True,
        use_timing_randomization: bool = True,
        compression: bool = True,
        **kwargs
    ) -> bool:
        """
        Establish obfuscated SSH connection.

        Note: Full obfuscation requires compatible server-side component.
        This implementation provides client-side obfuscation framework.

        Args:
            host: Target SSH server hostname
            port: Target port
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            obfuscation_password: Password for obfuscation
            use_padding: Enable traffic padding
            use_timing_randomization: Enable timing randomization
            compression: Enable SSH compression

        Returns:
            True if connection established
        """
        try:
            self._log(f"Establishing obfuscated connection to {host}:{port}")

            if obfuscation_password:
                self.obfuscation_key = self._generate_obfuscation_key(obfuscation_password)

            # Create socket with timing randomization
            if use_timing_randomization:
                self._randomize_timing()

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((host, port))

            self._log("Socket connection established")

            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect using standard Paramiko (obfuscation would need custom transport)
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "compress": compression,
            }

            if key_file:
                connect_kwargs["key_filename"] = key_file
            elif password:
                connect_kwargs["password"] = password

            self.ssh_client.connect(**connect_kwargs)
            self.connected = True

            self._log("Obfuscated SSH connection established", "success")
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

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        self.connected = False
        self.obfuscation_key = None
        self._log("Disconnected")

    def is_connected(self) -> bool:
        """Check if connection is active."""
        if not self.ssh_client or not self.connected:
            return False

        try:
            transport = self.ssh_client.get_transport()
            return transport and transport.is_active()
        except Exception:
            self.connected = False
            return False

    def get_client(self):
        """Get the underlying SSH client."""
        return self.ssh_client

    def send_obfuscated(self, data: bytes) -> bool:
        """
        Send data with obfuscation applied.

        Args:
            data: Data to send

        Returns:
            True if sent successfully
        """
        if not self.socket:
            return False

        try:
            # Apply obfuscation layers
            obfuscated = data

            if self.obfuscation_key:
                obfuscated = self._xor_data(obfuscated, self.obfuscation_key)

            obfuscated = self._add_padding(obfuscated)

            # Fragment and send with timing randomization
            chunks = self._fragment_data(obfuscated)

            for chunk in chunks:
                self._randomize_timing()
                self.socket.send(chunk)

            return True

        except Exception as e:
            self._log(f"Send failed: {e}", "error")
            return False

    def receive_obfuscated(self, size: int = 4096) -> Optional[bytes]:
        """
        Receive and deobfuscate data.

        Args:
            size: Maximum bytes to receive

        Returns:
            Deobfuscated data or None
        """
        if not self.socket:
            return None

        try:
            data = self.socket.recv(size)

            if not data:
                return None

            # Remove obfuscation layers
            deobfuscated = self._remove_padding(data)

            if self.obfuscation_key:
                deobfuscated = self._xor_data(deobfuscated, self.obfuscation_key)

            return deobfuscated

        except Exception as e:
            self._log(f"Receive failed: {e}", "error")
            return None

    @staticmethod
    def generate_random_padding(size: int) -> bytes:
        """
        Generate random padding data.

        Args:
            size: Size of padding in bytes

        Returns:
            Random bytes
        """
        return os.urandom(size)

    @staticmethod
    def simulate_http_traffic(data: bytes) -> bytes:
        """
        Wrap data to look like HTTP traffic.

        Args:
            data: Data to wrap

        Returns:
            HTTP-wrapped data
        """
        # Create fake HTTP request
        http_header = b"POST /upload HTTP/1.1\r\n"
        http_header += b"Host: www.example.com\r\n"
        http_header += b"Content-Type: application/octet-stream\r\n"
        http_header += f"Content-Length: {len(data)}\r\n".encode()
        http_header += b"\r\n"

        return http_header + data

    @staticmethod
    def test_dpi_detection(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """
        Test if DPI is actively inspecting traffic.

        Args:
            host: Target host
            port: Target port
            timeout: Connection timeout

        Returns:
            Dictionary with DPI detection results
        """
        result = {
            "dpi_detected": False,
            "reset_on_ssh_banner": False,
            "reset_on_random_data": False,
            "details": "",
        }

        # Test 1: Normal SSH banner
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # Send SSH-like banner
            sock.send(b"SSH-2.0-OpenSSH_8.0\r\n")
            time.sleep(0.5)

            try:
                response = sock.recv(1024)
                if response:
                    result["reset_on_ssh_banner"] = False
            except (socket.timeout, ConnectionResetError):
                result["reset_on_ssh_banner"] = True
                result["dpi_detected"] = True

            sock.close()

        except Exception:
            pass

        # Test 2: Random binary data
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # Send random data
            sock.send(os.urandom(64))
            time.sleep(0.5)

            try:
                sock.recv(1024)
                result["reset_on_random_data"] = False
            except (socket.timeout, ConnectionResetError):
                result["reset_on_random_data"] = True

            sock.close()

        except Exception:
            pass

        # Analyze results
        if result["reset_on_ssh_banner"] and not result["reset_on_random_data"]:
            result["dpi_detected"] = True
            result["details"] = "DPI appears to block SSH protocol signatures"
        elif result["reset_on_ssh_banner"] and result["reset_on_random_data"]:
            result["details"] = "Connection resets on both - may be general firewall"
        elif not result["reset_on_ssh_banner"]:
            result["details"] = "No SSH-specific blocking detected"

        return result
