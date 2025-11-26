"""
HTTP Tunnel Method

SSH through HTTP CONNECT proxy for bypassing network restrictions.
"""

import base64
import socket
import ssl
import time
from typing import Any, Dict, Optional

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class HTTPTunnel:
    """
    HTTP CONNECT tunnel handler for SSH connections.

    This method uses HTTP CONNECT method to tunnel SSH through
    HTTP/HTTPS proxies, which are often allowed in restricted networks.
    """

    METHOD_NAME = "http_tunnel"
    DESCRIPTION = "SSH through HTTP CONNECT proxy"

    def __init__(self, logger=None):
        """
        Initialize HTTPTunnel handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.tunnel_socket = None
        self.ssh_client = None
        self.connected = False

        if not PARAMIKO_AVAILABLE:
            raise ImportError("paramiko is required. Install with: pip install paramiko")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="HTTPTunnel")

    def _create_http_connect_request(
        self,
        host: str,
        port: int,
        proxy_auth: Optional[tuple] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> bytes:
        """
        Create HTTP CONNECT request.

        Args:
            host: Target host
            port: Target port
            proxy_auth: Tuple of (username, password) for proxy authentication
            custom_headers: Additional headers to include

        Returns:
            HTTP CONNECT request as bytes
        """
        request = f"CONNECT {host}:{port} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
        request += "Proxy-Connection: Keep-Alive\r\n"

        if proxy_auth:
            credentials = base64.b64encode(f"{proxy_auth[0]}:{proxy_auth[1]}".encode()).decode()
            request += f"Proxy-Authorization: Basic {credentials}\r\n"

        if custom_headers:
            for key, value in custom_headers.items():
                request += f"{key}: {value}\r\n"

        request += "\r\n"
        return request.encode()

    def _parse_http_response(self, response: bytes) -> tuple:
        """
        Parse HTTP response from proxy.

        Args:
            response: HTTP response bytes

        Returns:
            Tuple of (status_code, status_message, headers)
        """
        try:
            response_str = response.decode("utf-8", errors="ignore")
            lines = response_str.split("\r\n")

            # Parse status line
            status_line = lines[0]
            parts = status_line.split(" ", 2)
            status_code = int(parts[1])
            status_message = parts[2] if len(parts) > 2 else ""

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key.lower()] = value

            return status_code, status_message, headers

        except Exception:
            return 0, "Parse error", {}

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        proxy_host: Optional[str] = None,
        proxy_port: int = 8080,
        proxy_auth: Optional[tuple] = None,
        use_ssl: bool = False,
        target_ssh_port: int = 22,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if HTTP CONNECT tunnel is possible.

        Args:
            host: SSH server hostname
            port: Proxy port (overridden by proxy_port if proxy_host is set)
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            proxy_host: HTTP proxy host (if different from target)
            proxy_port: HTTP proxy port
            proxy_auth: Proxy authentication (username, password)
            use_ssl: Use HTTPS for proxy connection
            target_ssh_port: Target SSH port on the server

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

        # Determine proxy settings
        actual_proxy_host = proxy_host or host
        actual_proxy_port = proxy_port if proxy_host else port

        start_time = time.time()

        try:
            self._log(f"Testing HTTP CONNECT through {actual_proxy_host}:{actual_proxy_port}")

            # Create socket to proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((actual_proxy_host, actual_proxy_port))

            # Wrap in SSL if needed
            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=actual_proxy_host)

            # Send HTTP CONNECT request
            connect_request = self._create_http_connect_request(
                host, target_ssh_port, proxy_auth
            )
            sock.send(connect_request)

            # Receive response
            response = sock.recv(4096)
            status_code, status_message, headers = self._parse_http_response(response)

            connect_latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(connect_latency, 2)

            if status_code == 200:
                # Tunnel established
                self._log(f"HTTP CONNECT successful: {status_code} {status_message}")

                # Check for SSH banner
                sock.settimeout(3)
                try:
                    banner = sock.recv(256)
                    if banner.startswith(b"SSH-"):
                        result["status"] = "success"
                        result["details"] = f"Tunnel established in {connect_latency:.0f}ms"
                        self._log("SSH banner received through tunnel", "success")
                    else:
                        result["status"] = "success"
                        result["details"] = f"Tunnel established (no SSH banner)"
                except socket.timeout:
                    result["status"] = "success"
                    result["details"] = f"Tunnel established in {connect_latency:.0f}ms"

            elif status_code == 407:
                result["error"] = "Proxy authentication required"
                result["details"] = "Proxy requires authentication"
                self._log("Proxy authentication required", "warning")

            elif status_code == 403:
                result["error"] = "Forbidden by proxy"
                result["details"] = "Proxy denied CONNECT to target"
                self._log("Proxy denied connection", "error")

            else:
                result["error"] = f"HTTP {status_code}: {status_message}"
                result["details"] = "Proxy rejected CONNECT request"
                self._log(f"Proxy error: {status_code} {status_message}", "error")

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
        proxy_host: Optional[str] = None,
        proxy_port: int = 8080,
        proxy_auth: Optional[tuple] = None,
        use_ssl: bool = False,
        target_ssh_port: int = 22,
        compression: bool = True,
        **kwargs
    ) -> bool:
        """
        Establish HTTP CONNECT tunnel and SSH connection.

        Args:
            host: SSH server hostname
            port: Port (proxy_port takes precedence)
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            proxy_host: HTTP proxy host
            proxy_port: HTTP proxy port
            proxy_auth: Proxy authentication
            use_ssl: Use HTTPS
            target_ssh_port: Target SSH port
            compression: Enable SSH compression

        Returns:
            True if connection established
        """
        actual_proxy_host = proxy_host or host
        actual_proxy_port = proxy_port if proxy_host else port

        try:
            self._log(f"Connecting through HTTP proxy {actual_proxy_host}:{actual_proxy_port}")

            # Create socket to proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((actual_proxy_host, actual_proxy_port))

            # Wrap in SSL if needed
            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=actual_proxy_host)

            # Send HTTP CONNECT request
            connect_request = self._create_http_connect_request(
                host, target_ssh_port, proxy_auth
            )
            sock.send(connect_request)

            # Receive response
            response = sock.recv(4096)
            status_code, status_message, _ = self._parse_http_response(response)

            if status_code != 200:
                self._log(f"Proxy rejected: {status_code} {status_message}", "error")
                sock.close()
                return False

            self._log("HTTP tunnel established")
            self.tunnel_socket = sock

            # Create SSH connection through tunnel
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            transport = paramiko.Transport(self.tunnel_socket)
            transport.connect(
                username=username,
                password=password,
                pkey=paramiko.RSAKey.from_private_key_file(key_file) if key_file else None
            )

            self.ssh_client._transport = transport
            self.connected = True

            self._log("SSH over HTTP tunnel established", "success")
            return True

        except Exception as e:
            self._log(f"Connection failed: {e}", "error")
            self.disconnect()
            return False

    def disconnect(self):
        """Close the HTTP tunnel."""
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None

        if self.tunnel_socket:
            try:
                self.tunnel_socket.close()
            except Exception:
                pass
            self.tunnel_socket = None

        self.connected = False
        self._log("Disconnected")

    def is_connected(self) -> bool:
        """Check if tunnel is active."""
        if not self.tunnel_socket or not self.connected:
            return False

        try:
            self.tunnel_socket.getpeername()
            return True
        except Exception:
            self.connected = False
            return False

    def get_client(self):
        """Get the underlying SSH client."""
        return self.ssh_client

    @staticmethod
    def test_proxy(
        proxy_host: str,
        proxy_port: int,
        target_host: str = "www.google.com",
        target_port: int = 443,
        timeout: int = 5
    ) -> bool:
        """
        Test if HTTP proxy allows CONNECT method.

        Args:
            proxy_host: Proxy hostname
            proxy_port: Proxy port
            target_host: Target to connect through proxy
            target_port: Target port
            timeout: Connection timeout

        Returns:
            True if proxy allows CONNECT
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((proxy_host, proxy_port))

            request = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
            request += f"Host: {target_host}:{target_port}\r\n"
            request += "\r\n"
            sock.send(request.encode())

            response = sock.recv(1024).decode("utf-8", errors="ignore")
            sock.close()

            return "200" in response

        except Exception:
            return False

    @staticmethod
    def find_http_proxies(ports: list, timeout: int = 2) -> list:
        """
        Find common HTTP proxy ports on localhost.

        Args:
            ports: List of ports to check
            timeout: Connection timeout

        Returns:
            List of ports that respond as HTTP proxies
        """
        proxy_ports = []

        for port in ports:
            if HTTPTunnel.test_proxy("127.0.0.1", port, timeout=timeout):
                proxy_ports.append(port)

        return proxy_ports
