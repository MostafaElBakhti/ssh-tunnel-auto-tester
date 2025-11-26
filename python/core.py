"""
Core Orchestrator Module

Main orchestrator for SSH tunnel testing and connection management.
"""

import asyncio
import json
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .utils.logger import TunnelLogger
from .utils.config_parser import ConfigParser, ConfigError
from .utils.network_detector import NetworkDetector
from .utils.speed_test import SpeedTest

# Import methods with graceful degradation
from .methods.direct_ssh import DirectSSH

try:
    from .methods.websocket_tunnel import WebSocketTunnel
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    from .methods.ssl_wrapper import SSLWrapper
    SSL_WRAPPER_AVAILABLE = True
except ImportError:
    SSL_WRAPPER_AVAILABLE = False

try:
    from .methods.http_tunnel import HTTPTunnel
    HTTP_TUNNEL_AVAILABLE = True
except ImportError:
    HTTP_TUNNEL_AVAILABLE = False

try:
    from .methods.dns_tunnel import DNSTunnel
    DNS_TUNNEL_AVAILABLE = True
except ImportError:
    DNS_TUNNEL_AVAILABLE = False

try:
    from .methods.sni_spoof import SNISpoof
    SNI_SPOOF_AVAILABLE = True
except ImportError:
    SNI_SPOOF_AVAILABLE = False

try:
    from .methods.obfuscation import Obfuscation
    OBFUSCATION_AVAILABLE = True
except ImportError:
    OBFUSCATION_AVAILABLE = False


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Pauses testing after consecutive failures to avoid IP bans.
    """

    def __init__(self, failure_threshold: int = 5, pause_duration: int = 30):
        self.failure_threshold = failure_threshold
        self.pause_duration = pause_duration
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False

    def record_failure(self):
        """Record a failure and check if circuit should open."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True

    def record_success(self):
        """Record a success, reset failure count."""
        self.failure_count = 0
        self.is_open = False

    def should_allow(self) -> bool:
        """Check if requests should be allowed."""
        if not self.is_open:
            return True

        # Check if pause duration has passed
        if time.time() - self.last_failure_time >= self.pause_duration:
            self.is_open = False
            self.failure_count = 0
            return True

        return False

    def get_wait_time(self) -> int:
        """Get remaining wait time in seconds."""
        if not self.is_open:
            return 0

        elapsed = time.time() - self.last_failure_time
        return max(0, int(self.pause_duration - elapsed))


class TunnelTester:
    """
    Main orchestrator for SSH tunnel testing.

    This class coordinates testing of multiple SSH tunneling methods
    and manages connections.
    """

    # Method name to class mapping
    METHOD_CLASSES = {
        "direct": DirectSSH,
        "websocket": WebSocketTunnel if WEBSOCKET_AVAILABLE else None,
        "ssl_wrap": SSLWrapper if SSL_WRAPPER_AVAILABLE else None,
        "http_tunnel": HTTPTunnel if HTTP_TUNNEL_AVAILABLE else None,
        "dns_tunnel": DNSTunnel if DNS_TUNNEL_AVAILABLE else None,
        "sni_spoof": SNISpoof if SNI_SPOOF_AVAILABLE else None,
        "obfuscated": Obfuscation if OBFUSCATION_AVAILABLE else None,
    }

    def __init__(
        self,
        config: Optional[ConfigParser] = None,
        config_path: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False,
    ):
        """
        Initialize TunnelTester.

        Args:
            config: Pre-loaded configuration
            config_path: Path to configuration file
            verbose: Enable verbose output
            quiet: Suppress non-essential output
        """
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = ConfigParser(config_path)
        else:
            self.config = ConfigParser()  # Use defaults

        # Override verbose/quiet from arguments
        if verbose:
            self.config.set("verbose", True)
        if quiet:
            self.config.set("quiet", True)

        # Initialize logger
        self.logger = TunnelLogger(
            log_file=self.config.get("log_file"),
            level=self.config.get("log_level", "INFO"),
            colorize=self.config.get("colorize", True),
            verbose=self.config.get("verbose", False),
            quiet=self.config.get("quiet", False),
        )

        # Initialize components
        self.network_detector = NetworkDetector(logger=self.logger)
        self.speed_test = SpeedTest(
            test_size=self.config.get("speed_test.test_size", 10240),
            min_speed=self.config.get("speed_test.min_speed", 1024),
            logger=self.logger,
        )

        # Initialize circuit breaker
        cb_config = self.config.get("circuit_breaker", {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get("failure_threshold", 5),
            pause_duration=cb_config.get("pause_duration", 30),
        )

        # State
        self.results: List[Dict[str, Any]] = []
        self.active_connection = None
        self.active_method = None
        self._stop_requested = False
        self._cache_file = self.config.get("cache.file", ".cache.json")
        self._cache = self._load_cache()

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.warning("Shutdown signal received, cleaning up...")
            self._stop_requested = True
            self.disconnect()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _load_cache(self) -> Dict:
        """Load cached successful methods."""
        if not self.config.get("cache.enabled", True):
            return {}

        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r") as f:
                    cache = json.load(f)

                # Check cache age
                max_age = self.config.get("cache.max_age", 86400)
                cache_time = cache.get("timestamp", 0)
                if time.time() - cache_time > max_age:
                    return {}

                return cache
        except Exception:
            pass

        return {}

    def _save_cache(self, method: str, host: str, port: int):
        """Save successful method to cache."""
        if not self.config.get("cache.enabled", True):
            return

        try:
            cache = {
                "timestamp": time.time(),
                "method": method,
                "host": host,
                "port": port,
            }
            with open(self._cache_file, "w") as f:
                json.dump(cache, f)
        except Exception:
            pass

    def get_available_methods(self) -> List[str]:
        """Get list of available (installed) methods."""
        available = []
        for method_name, method_class in self.METHOD_CLASSES.items():
            if method_class is not None:
                available.append(method_name)
        return available

    def get_unavailable_methods(self) -> Dict[str, str]:
        """Get methods that are unavailable and why."""
        unavailable = {}

        if not WEBSOCKET_AVAILABLE:
            unavailable["websocket"] = "websocket-client not installed"
        if not DNS_TUNNEL_AVAILABLE:
            unavailable["dns_tunnel"] = "dnspython not installed"

        return unavailable

    def detect_network(self) -> Dict[str, Any]:
        """
        Detect current network type and conditions.

        Returns:
            Network information dictionary
        """
        self.logger.info("Detecting network...")
        network_info = self.network_detector.detect_network_type()

        # Check internet connectivity
        connected, latency = self.network_detector.check_internet_connectivity()
        network_info["internet_connected"] = connected
        network_info["internet_latency_ms"] = latency

        if connected:
            self.logger.success(f"Internet connected (latency: {latency:.0f}ms)")
        else:
            self.logger.error("No internet connectivity detected")

        # Get public IP
        if connected:
            public_ip = self.network_detector.get_public_ip()
            network_info["public_ip"] = public_ip
            if public_ip:
                self.logger.info(f"Public IP: {public_ip}")

        return network_info

    def _create_method_instance(self, method_name: str):
        """Create an instance of a tunnel method."""
        method_class = self.METHOD_CLASSES.get(method_name)
        if method_class is None:
            return None

        try:
            return method_class(logger=self.logger)
        except ImportError as e:
            self.logger.debug(f"Cannot create {method_name}: {e}")
            return None

    def test_method(
        self,
        method_name: str,
        account: Dict[str, Any],
        port: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test a single tunneling method.

        Args:
            method_name: Name of the method to test
            account: SSH account dictionary
            port: Override port to test
            **kwargs: Additional method-specific arguments

        Returns:
            Test result dictionary
        """
        method_instance = self._create_method_instance(method_name)

        if method_instance is None:
            return {
                "method": method_name,
                "status": "skipped",
                "error": "Method not available",
                "details": "Required dependencies not installed",
            }

        test_port = port or account.get("port", 22)

        try:
            result = method_instance.test_connection(
                host=account["host"],
                port=test_port,
                username=account["username"],
                password=account.get("password"),
                key_file=account.get("key_file"),
                timeout=self.config.get_timeout(),
                sni_domains=self.config.get_sni_domains(),
                **kwargs
            )

            # Update circuit breaker
            if result.get("status") == "success":
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()

            return result

        except Exception as e:
            self.circuit_breaker.record_failure()
            return {
                "method": method_name,
                "status": "failed",
                "error": str(e),
                "details": f"Exception: {type(e).__name__}",
            }

    def test_all_methods(
        self,
        account: Optional[Dict[str, Any]] = None,
        methods: Optional[List[str]] = None,
        ports: Optional[List[int]] = None,
        parallel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Test all specified tunneling methods.

        Args:
            account: SSH account to test (uses first from config if not specified)
            methods: List of methods to test (uses config if not specified)
            ports: List of ports to test (uses config if not specified)
            parallel: Use parallel testing

        Returns:
            List of test results
        """
        # Get account
        if account is None:
            accounts = self.config.get_ssh_accounts()
            if not accounts:
                self.logger.error("No SSH accounts configured")
                return []
            account = accounts[0]

        # Get methods to test
        test_methods = methods or self.config.get_test_modes()
        available_methods = self.get_available_methods()
        test_methods = [m for m in test_methods if m in available_methods]

        # Get ports to test
        test_ports = ports or self.config.get_ports()

        self.logger.header("SSH Tunnel Auto-Tester")
        self.logger.info(f"Testing {len(test_methods)} methods on {len(test_ports)} ports")
        self.logger.info(f"Target: {account['host']}")
        self.logger.subheader("Testing Methods")

        results = []
        total_tests = len(test_methods) * len(test_ports)
        completed = 0

        if parallel:
            max_workers = self.config.get_max_threads()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}

                for method in test_methods:
                    for port in test_ports:
                        # Check circuit breaker
                        if not self.circuit_breaker.should_allow():
                            wait_time = self.circuit_breaker.get_wait_time()
                            self.logger.warning(f"Circuit breaker open, waiting {wait_time}s...")
                            time.sleep(wait_time)

                        future = executor.submit(self.test_method, method, account, port)
                        futures[future] = (method, port)

                for future in as_completed(futures):
                    method, port = futures[future]
                    try:
                        result = future.result()
                        result["port"] = port
                        results.append(result)

                        # Log result
                        status = result.get("status", "unknown")
                        details = result.get("details", "")
                        self.logger.result_line(f"{method}:{port}", status, details)

                    except Exception as e:
                        results.append({
                            "method": method,
                            "port": port,
                            "status": "failed",
                            "error": str(e),
                        })

                    completed += 1
                    self.logger.progress_bar(completed, total_tests, prefix="Progress: ")

        else:
            for method in test_methods:
                for port in test_ports:
                    if self._stop_requested:
                        break

                    # Check circuit breaker
                    if not self.circuit_breaker.should_allow():
                        wait_time = self.circuit_breaker.get_wait_time()
                        self.logger.warning(f"Circuit breaker open, waiting {wait_time}s...")
                        time.sleep(wait_time)

                    self.logger.testing(f"Testing {method} on port {port}...")

                    result = self.test_method(method, account, port)
                    result["port"] = port
                    results.append(result)

                    status = result.get("status", "unknown")
                    details = result.get("details", "")
                    self.logger.result_line(f"{method}:{port}", status, details)

                    completed += 1
                    self.logger.progress_bar(completed, total_tests, prefix="Progress: ")

                    # Add delay between tests
                    delay = self.config.get("connection_delay", 1)
                    time.sleep(delay)

        self.results = results
        return results

    def find_working_method(
        self,
        account: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first working tunneling method.

        Args:
            account: SSH account to test

        Returns:
            First successful result or None
        """
        # Check cache first
        if self._cache.get("method"):
            cached_method = self._cache["method"]
            cached_host = self._cache.get("host")

            if account and account.get("host") == cached_host:
                self.logger.info(f"Trying cached method: {cached_method}")
                result = self.test_method(cached_method, account)
                if result.get("status") == "success":
                    self.logger.success(f"Cached method {cached_method} still works!")
                    return result

        # Test all methods
        results = self.test_all_methods(account=account, parallel=False)

        for result in results:
            if result.get("status") == "success":
                # Cache successful method
                self._save_cache(
                    result["method"],
                    result.get("host", ""),
                    result.get("port", 22),
                )
                return result

        return None

    def connect(
        self,
        method: str,
        account: Dict[str, Any],
        port: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Establish SSH connection using specified method.

        Args:
            method: Tunneling method to use
            account: SSH account
            port: Port to connect to
            **kwargs: Additional method arguments

        Returns:
            True if connection established
        """
        method_instance = self._create_method_instance(method)
        if method_instance is None:
            self.logger.error(f"Method {method} not available")
            return False

        connect_port = port or account.get("port", 22)

        self.logger.info(f"Connecting via {method} to {account['host']}:{connect_port}...")

        success = method_instance.connect(
            host=account["host"],
            port=connect_port,
            username=account["username"],
            password=account.get("password"),
            key_file=account.get("key_file"),
            timeout=self.config.get_timeout(),
            compression=self.config.get("compression", True),
            **kwargs
        )

        if success:
            self.active_connection = method_instance
            self.active_method = method
            self.logger.success(f"Connected via {method}")

            # Run speed test if enabled
            if self.config.get("speed_test.enabled", True):
                client = method_instance.get_client()
                if client:
                    self.logger.info("Running connection quality test...")
                    quality = self.speed_test.test_tunnel_quality(client)
                    self.logger.info(f"Quality score: {quality['quality_score']}/100")
                    self.logger.info(quality["recommendation"])

            return True
        else:
            self.logger.error(f"Failed to connect via {method}")
            return False

    def disconnect(self):
        """Disconnect active connection."""
        if self.active_connection:
            try:
                self.active_connection.disconnect()
                self.logger.info("Disconnected")
            except Exception as e:
                self.logger.debug(f"Disconnect error: {e}")
            finally:
                self.active_connection = None
                self.active_method = None

    def find_and_connect(
        self,
        account: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Find working method and establish connection.

        Args:
            account: SSH account to use

        Returns:
            True if connected successfully
        """
        if account is None:
            accounts = self.config.get_ssh_accounts()
            if not accounts:
                self.logger.error("No SSH accounts configured")
                return False
            account = accounts[0]

        self.logger.header("Find and Connect")

        # Find working method
        result = self.find_working_method(account)

        if result is None:
            self.logger.error("No working method found")
            return False

        # Connect using the working method
        return self.connect(
            method=result["method"],
            account=account,
            port=result.get("port"),
        )

    def keep_alive_loop(self, interval: int = 60):
        """
        Keep-alive loop for maintaining connection.

        Args:
            interval: Seconds between keep-alive checks
        """
        if not self.active_connection:
            self.logger.error("No active connection for keep-alive")
            return

        self.logger.info(f"Starting keep-alive (interval: {interval}s)")

        while not self._stop_requested:
            if not self.active_connection.is_connected():
                self.logger.warning("Connection lost, attempting reconnect...")

                # Try to reconnect
                if self.config.get("auto_reconnect", True):
                    max_attempts = self.config.get("max_reconnect_attempts", 5)
                    reconnected = False

                    for attempt in range(max_attempts):
                        self.logger.info(f"Reconnect attempt {attempt + 1}/{max_attempts}")
                        if self.find_and_connect():
                            reconnected = True
                            break
                        time.sleep(5)

                    if not reconnected:
                        self.logger.error("Failed to reconnect after all attempts")
                        break
            else:
                self.logger.debug("Connection alive")

            time.sleep(interval)

    def export_results(
        self,
        filepath: Optional[str] = None,
        format: str = "json",
    ):
        """
        Export test results to file.

        Args:
            filepath: Output file path
            format: Export format (json or csv)
        """
        if not self.results:
            self.logger.warning("No results to export")
            return

        export_config = self.config.get("export", {})
        filepath = filepath or export_config.get("file", "results.json")
        format = format or export_config.get("format", "json")

        # Add metadata if enabled
        export_data = {
            "results": self.results,
        }

        if export_config.get("include_timestamps", True):
            export_data["timestamp"] = datetime.now().isoformat()

        if export_config.get("include_metrics", True):
            export_data["summary"] = {
                "total": len(self.results),
                "success": sum(1 for r in self.results if r.get("status") == "success"),
                "failed": sum(1 for r in self.results if r.get("status") == "failed"),
                "skipped": sum(1 for r in self.results if r.get("status") == "skipped"),
            }

        if format == "json":
            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2)
        elif format == "csv":
            import csv
            with open(filepath, "w", newline="") as f:
                if self.results:
                    writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                    writer.writeheader()
                    writer.writerows(self.results)

        self.logger.success(f"Results exported to {filepath}")

    def print_summary(self):
        """Print summary of test results."""
        if not self.results:
            self.logger.info("No results to summarize")
            return

        self.logger.summary_table(self.results)

        # Print working methods
        working = [r for r in self.results if r.get("status") == "success"]
        if working:
            self.logger.subheader("Working Methods")
            for result in working:
                method = result.get("method", "unknown")
                port = result.get("port", "?")
                latency = result.get("latency_ms", "?")
                self.logger.success(f"{method} on port {port} (latency: {latency}ms)")
