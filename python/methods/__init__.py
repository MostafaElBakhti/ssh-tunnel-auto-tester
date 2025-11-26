"""
SSH Tunnel Connection Methods Package

This package contains implementations of various tunneling methods:
- direct_ssh: Standard SSH connection
- websocket_tunnel: SSH over WebSocket
- ssl_wrapper: SSH wrapped in SSL/TLS
- http_tunnel: SSH through HTTP CONNECT
- dns_tunnel: SSH through DNS queries
- sni_spoof: SNI spoofing techniques
- obfuscation: Traffic obfuscation methods
"""

from .direct_ssh import DirectSSH
from .websocket_tunnel import WebSocketTunnel
from .ssl_wrapper import SSLWrapper
from .http_tunnel import HTTPTunnel
from .dns_tunnel import DNSTunnel
from .sni_spoof import SNISpoof
from .obfuscation import Obfuscation

__all__ = [
    "DirectSSH",
    "WebSocketTunnel",
    "SSLWrapper",
    "HTTPTunnel",
    "DNSTunnel",
    "SNISpoof",
    "Obfuscation",
]
