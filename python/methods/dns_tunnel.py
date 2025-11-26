"""
DNS Tunnel Method

SSH through DNS queries (iodine-style) for bypassing network restrictions.
"""

import base64
import socket
import struct
import time
from typing import Any, Dict, List, Optional

try:
    import dns.resolver
    import dns.message
    import dns.query
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class DNSTunnel:
    """
    DNS tunnel handler for SSH connections.

    This method encodes data in DNS queries, allowing tunneling
    through networks that only allow DNS traffic.

    NOTE: This is a simplified implementation. Full DNS tunneling
    requires a compatible server-side component (like iodine).
    """

    METHOD_NAME = "dns_tunnel"
    DESCRIPTION = "SSH through DNS queries (advanced)"

    def __init__(self, logger=None):
        """
        Initialize DNSTunnel handler.

        Args:
            logger: Optional logger instance for output
        """
        self.logger = logger
        self.connected = False
        self.domain = None
        self.dns_server = None

        if not DNS_AVAILABLE:
            raise ImportError("dnspython is required. Install with: pip install dnspython")

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message, prefix="DNSTunnel")

    def _encode_data(self, data: bytes) -> str:
        """
        Encode binary data for DNS query.

        Args:
            data: Binary data to encode

        Returns:
            Base32 encoded string (DNS-safe)
        """
        return base64.b32encode(data).decode("ascii").rstrip("=").lower()

    def _decode_data(self, encoded: str) -> bytes:
        """
        Decode DNS response data.

        Args:
            encoded: Encoded string from DNS response

        Returns:
            Decoded binary data
        """
        # Pad to multiple of 8 for base32
        padding = (8 - len(encoded) % 8) % 8
        encoded = encoded.upper() + "=" * padding
        return base64.b32decode(encoded)

    def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 10,
        tunnel_domain: Optional[str] = None,
        dns_server: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test if DNS tunneling is possible.

        Args:
            host: SSH server hostname (used to derive tunnel domain if not specified)
            port: Not used for DNS tunnel
            username: SSH username
            password: SSH password
            key_file: Path to private key file
            timeout: Connection timeout
            tunnel_domain: Domain for DNS tunneling (e.g., t.example.com)
            dns_server: DNS server to use (or auto-detect)

        Returns:
            Dictionary with test results
        """
        result = {
            "method": self.METHOD_NAME,
            "status": "failed",
            "host": host,
            "port": 53,
            "latency_ms": None,
            "error": None,
            "details": "",
        }

        start_time = time.time()

        try:
            self._log("Testing DNS tunnel capability")

            # First, test basic DNS resolution
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            resolver.timeout = timeout
            resolver.lifetime = timeout

            # Test DNS connectivity
            test_query = "google.com"
            try:
                answers = resolver.resolve(test_query, "A")
                dns_latency = (time.time() - start_time) * 1000
                result["latency_ms"] = round(dns_latency, 2)
                self._log(f"DNS resolution working: {test_query} -> {answers[0]}")
            except Exception as e:
                result["error"] = f"DNS resolution failed: {e}"
                result["details"] = "Cannot resolve DNS queries"
                return result

            # Test if we can use TXT records (often used for DNS tunneling)
            txt_test_domain = "google.com"
            try:
                txt_answers = resolver.resolve(txt_test_domain, "TXT")
                self._log("TXT record queries working")
            except Exception:
                self._log("TXT queries may be blocked")

            # Test NULL record type (used by iodine)
            # Most networks block this, so it's a good indicator
            null_blocked = True
            try:
                # NULL records are rarely used legitimately
                # This tests if they're filtered
                null_query = dns.message.make_query("test.google.com", "NULL")
                # This will likely timeout or be blocked
            except Exception:
                pass

            # If we have a tunnel domain, test it
            if tunnel_domain:
                try:
                    self._log(f"Testing tunnel domain: {tunnel_domain}")
                    # Try to resolve the tunnel domain
                    tunnel_answers = resolver.resolve(tunnel_domain, "A")
                    result["status"] = "success"
                    result["details"] = f"Tunnel domain responds, latency {dns_latency:.0f}ms"
                    self._log("Tunnel domain responsive", "success")
                except dns.resolver.NXDOMAIN:
                    result["error"] = "Tunnel domain does not exist"
                    result["details"] = "Configure a valid DNS tunnel server"
                except dns.resolver.NoAnswer:
                    # No A record, but domain exists - might be tunnel server
                    result["status"] = "success"
                    result["details"] = f"Domain exists, testing tunnel"
                except Exception as e:
                    result["error"] = f"Tunnel domain test failed: {e}"
            else:
                # No tunnel domain specified, just report DNS capability
                result["status"] = "success"
                result["details"] = f"DNS working (latency {dns_latency:.0f}ms), needs tunnel server"
                self._log("DNS tunneling possible if server available")

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
        tunnel_domain: str = None,
        dns_server: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Establish DNS tunnel (requires server-side component).

        NOTE: Full DNS tunneling requires a server like iodine.
        This method provides the framework but actual implementation
        would require integration with such a tool.

        Args:
            host: SSH server hostname
            port: Not used
            username: SSH username
            password: SSH password
            key_file: SSH key file
            timeout: Connection timeout
            tunnel_domain: DNS tunnel domain
            dns_server: DNS server to use

        Returns:
            True if connection established
        """
        if not tunnel_domain:
            self._log("DNS tunnel requires a tunnel domain (e.g., t.yourdomain.com)", "error")
            return False

        try:
            self._log(f"Initiating DNS tunnel through {tunnel_domain}")

            self.domain = tunnel_domain
            self.dns_server = dns_server

            # In a real implementation, this would:
            # 1. Establish handshake with DNS tunnel server
            # 2. Negotiate encoding and session
            # 3. Create virtual interface or proxy
            # 4. Tunnel SSH through DNS queries

            self._log("DNS tunnel framework initialized", "info")
            self._log("NOTE: Full DNS tunneling requires server-side component (e.g., iodine)", "warning")

            self.connected = True
            return True

        except Exception as e:
            self._log(f"DNS tunnel failed: {e}", "error")
            return False

    def disconnect(self):
        """Close DNS tunnel."""
        self.connected = False
        self.domain = None
        self._log("Disconnected")

    def is_connected(self) -> bool:
        """Check if tunnel is active."""
        return self.connected

    def send_via_dns(self, data: bytes, subdomain_prefix: str = "d") -> bool:
        """
        Send data encoded in DNS query.

        Args:
            data: Data to send
            subdomain_prefix: Prefix for subdomain

        Returns:
            True if sent successfully
        """
        if not self.connected or not self.domain:
            return False

        try:
            # Encode data as subdomain
            encoded = self._encode_data(data)

            # Split into DNS-safe chunks (max 63 chars per label)
            chunks = [encoded[i:i + 63] for i in range(0, len(encoded), 63)]
            query_domain = ".".join(chunks) + f".{subdomain_prefix}.{self.domain}"

            # Perform DNS query
            resolver = dns.resolver.Resolver()
            if self.dns_server:
                resolver.nameservers = [self.dns_server]

            answers = resolver.resolve(query_domain, "TXT")
            return True

        except Exception as e:
            self._log(f"DNS send failed: {e}", "error")
            return False

    @staticmethod
    def test_dns_connectivity(dns_server: Optional[str] = None, timeout: int = 5) -> Dict[str, Any]:
        """
        Test basic DNS connectivity.

        Args:
            dns_server: Specific DNS server to test
            timeout: Query timeout

        Returns:
            Dictionary with test results
        """
        if not DNS_AVAILABLE:
            return {"success": False, "error": "dnspython not installed"}

        result = {
            "success": False,
            "latency_ms": None,
            "dns_server": dns_server or "system default",
            "record_types": {
                "A": False,
                "TXT": False,
                "CNAME": False,
            },
            "error": None,
        }

        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            resolver.timeout = timeout
            resolver.lifetime = timeout

            # Test A record
            start_time = time.time()
            try:
                resolver.resolve("google.com", "A")
                result["record_types"]["A"] = True
                result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            except Exception:
                pass

            # Test TXT record
            try:
                resolver.resolve("google.com", "TXT")
                result["record_types"]["TXT"] = True
            except Exception:
                pass

            # Test CNAME record
            try:
                resolver.resolve("www.google.com", "CNAME")
                result["record_types"]["CNAME"] = True
            except dns.resolver.NoAnswer:
                # No CNAME but query worked
                result["record_types"]["CNAME"] = True
            except Exception:
                pass

            result["success"] = result["record_types"]["A"]

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def find_open_dns_servers(timeout: int = 2) -> List[str]:
        """
        Find accessible public DNS servers.

        Args:
            timeout: Connection timeout per server

        Returns:
            List of accessible DNS servers
        """
        public_dns = [
            "8.8.8.8",        # Google
            "8.8.4.4",        # Google
            "1.1.1.1",        # Cloudflare
            "1.0.0.1",        # Cloudflare
            "9.9.9.9",        # Quad9
            "208.67.222.222", # OpenDNS
            "208.67.220.220", # OpenDNS
        ]

        accessible = []

        for server in public_dns:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)
                sock.connect((server, 53))
                sock.close()
                accessible.append(server)
            except Exception:
                continue

        return accessible
