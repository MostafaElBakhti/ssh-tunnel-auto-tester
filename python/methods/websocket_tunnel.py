"""
WebSocket Tunnel Method

SSH over WebSocket protocol for bypassing network restrictions.
"""

import base64
import socket
import ssl
import threading
import time
from typing import Any, Dict, Optional

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class WebSocketTunnel:
    """
    WebSocket tunnel handler for SSH connections.

    This method encapsulates SSH traffic within WebSocket protocol,
    which is often allowed through restrictive firewalls.
    """

    METHOD_NAME = "websocket"
    DESCRIPTION = "SSH over WebSocket protocol"

    def __init__(self, logger=None):
        """
        Initialize WebSocketTunnel handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.ws = None
        self.ssh_client = None
        self.connected = False
        self._tunnel_thread = None
        self._stop_event = threading.Event()

        if not WEBSOCKET_AVAILABLE:
            raise ImportError("websocket-client is required. Install with: pip install websocket-client")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="WebSocket")

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        ws_path: str = "/ws",
        use_ssl: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if WebSocket tunnel is possible.

        Args:
            host: SSH server hostname or IP
            port: Port for WebSocket connection (usually 80 or 443)
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            ws_path: WebSocket endpoint path
            use_ssl: Use WSS (WebSocket Secure)

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

        # Build WebSocket URL
        protocol = "wss" if use_ssl else "ws"
        ws_url = f"{protocol}://{host}:{port}{ws_path}"

        try:
            self._log(f"Testing WebSocket connection to {ws_url}")

            # Test WebSocket connectivity
            ws = websocket.create_connection(
                ws_url,
                timeout=timeout,
                sslopt={"cert_reqs": ssl.CERT_NONE} if use_ssl else None,
                header={
                    "Host": host,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Origin": f"https://{host}" if use_ssl else f"http://{host}",
                }
            )

            ws_latency = (time.time() - start_time) * 1000

            # Send a test message
            ws.send("ping")
            ws.close()

            result["latency_ms"] = round(ws_latency, 2)
            result["status"] = "success"
            result["details"] = f"WebSocket connected in {ws_latency:.0f}ms"
            self._log(f"WebSocket connection successful", "success")

        except websocket.WebSocketBadStatusException as e:
            # Server responded but rejected WebSocket upgrade
            result["error"] = f"WebSocket upgrade rejected: {e}"
            result["details"] = "Server does not support WebSocket at this endpoint"
            self._log(f"WebSocket rejected: {e}", "error")

        except websocket.WebSocketConnectionClosedException:
            result["error"] = "Connection closed by server"
            result["details"] = "WebSocket connection was closed unexpectedly"
            self._log("Connection closed by server", "error")

        except socket.timeout:
            result["error"] = "Connection timed out"
            result["details"] = f"Timeout after {timeout}s"
            self._log(f"Connection timeout", "error")

        except ssl.SSLError as e:
            result["error"] = f"SSL error: {e}"
            result["details"] = "SSL/TLS handshake failed"
            self._log(f"SSL error: {e}", "error")

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
        ws_path: str = "/ws",
        use_ssl: bool = True,
        ssh_port: int = 22,
        **kwargs
    ) -> bool:
        """
        Establish WebSocket tunnel and SSH connection.

        Note: This requires a WebSocket-to-SSH proxy on the server side.
        For actual use, you would need a service like websockify or a
        custom proxy that bridges WebSocket to SSH.

        Args:
            host: Server hostname
            port: WebSocket port
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            ws_path: WebSocket endpoint path
            use_ssl: Use WSS
            ssh_port: Target SSH port on the server

        Returns:
            True if connection established
        """
        try:
            protocol = "wss" if use_ssl else "ws"
            ws_url = f"{protocol}://{host}:{port}{ws_path}"

            self._log(f"Connecting via WebSocket to {ws_url}")

            self.ws = websocket.create_connection(
                ws_url,
                timeout=timeout,
                sslopt={"cert_reqs": ssl.CERT_NONE} if use_ssl else None,
            )

            self.connected = True
            self._log("WebSocket tunnel established", "success")

            # Note: For actual SSH-over-WebSocket, you would need:
            # 1. A WebSocket-to-TCP proxy on the server
            # 2. Or use paramiko with a custom transport

            return True

        except Exception as e:
            self._log(f"Connection failed: {e}", "error")
            self.connected = False
            return False

    def disconnect(self):
        """Close the WebSocket tunnel."""
        self._stop_event.set()

        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None

        self.connected = False
        self._log("Disconnected")

    def is_connected(self) -> bool:
        """Check if tunnel is active."""
        if not self.ws or not self.connected:
            return False

        try:
            self.ws.ping()
            return True
        except Exception:
            self.connected = False
            return False

    def send_data(self, data: bytes) -> bool:
        """
        Send data through the WebSocket tunnel.

        Args:
            data: Data to send

        Returns:
            True if sent successfully
        """
        if not self.is_connected():
            return False

        try:
            # Encode binary data as base64 for WebSocket
            encoded = base64.b64encode(data).decode("utf-8")
            self.ws.send(encoded)
            return True
        except Exception as e:
            self._log(f"Send failed: {e}", "error")
            return False

    def receive_data(self, timeout: int = 5) -> Optional[bytes]:
        """
        Receive data from the WebSocket tunnel.

        Args:
            timeout: Receive timeout

        Returns:
            Received data or None
        """
        if not self.is_connected():
            return None

        try:
            self.ws.settimeout(timeout)
            data = self.ws.recv()

            # Decode base64 data
            if isinstance(data, str):
                return base64.b64decode(data)
            return data

        except websocket.WebSocketTimeoutException:
            return None
        except Exception as e:
            self._log(f"Receive failed: {e}", "error")
            return None

    @staticmethod
    def test_websocket_port(host: str, port: int, timeout: int = 5) -> bool:
        """
        Quick test if a port accepts WebSocket connections.

        Args:
            host: Target host
            port: Target port
            timeout: Connection timeout

        Returns:
            True if WebSocket connection possible
        """
        if not WEBSOCKET_AVAILABLE:
            return False

        for use_ssl in [True, False]:
            try:
                protocol = "wss" if use_ssl else "ws"
                url = f"{protocol}://{host}:{port}/"
                ws = websocket.create_connection(
                    url,
                    timeout=timeout,
                    sslopt={"cert_reqs": ssl.CERT_NONE} if use_ssl else None,
                )
                ws.close()
                return True
            except Exception:
                continue

        return False
