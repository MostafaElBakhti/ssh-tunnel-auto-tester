"""
Speed Test Module - Test connection speed and quality
"""

import socket
import time
from typing import Dict, Optional, Tuple


class SpeedTest:
    """
    Test connection speed and quality for SSH tunnels.
    """

    def __init__(
        self,
        test_size: int = 10240,
        min_speed: int = 1024,
        timeout: int = 30,
        logger=None
    ):
        """
        Initialize speed tester.

        Args:
            test_size: Size of test data in bytes
            min_speed: Minimum acceptable speed in bytes/sec
            timeout: Test timeout in seconds
            logger: Optional logger instance
        """
        self.test_size = test_size
        self.min_speed = min_speed
        self.timeout = timeout
        self.logger = logger

    def _log(self, message: str, level: str = "debug"):
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level, self.logger.debug)(message)

    def test_ssh_connection(self, ssh_client, test_data_size: int = None) -> Dict:
        """
        Test SSH connection speed by transferring data.

        Args:
            ssh_client: Paramiko SSH client
            test_data_size: Size of test data (uses default if not specified)

        Returns:
            Dictionary with speed test results
        """
        size = test_data_size or self.test_size
        test_data = b"X" * size

        result = {
            "success": False,
            "upload_speed": 0.0,
            "download_speed": 0.0,
            "latency_ms": 0.0,
            "error": None,
        }

        try:
            # Test latency with a simple command
            start_time = time.time()
            stdin, stdout, stderr = ssh_client.exec_command("echo test")
            stdout.read()
            latency = (time.time() - start_time) * 1000
            result["latency_ms"] = round(latency, 2)

            # Test upload/download via SFTP (if available)
            try:
                sftp = ssh_client.open_sftp()

                # Upload test
                remote_path = "/tmp/.tunnel_test_" + str(int(time.time()))
                start_time = time.time()
                with sftp.file(remote_path, "wb") as f:
                    f.write(test_data)
                upload_time = time.time() - start_time
                upload_speed = size / upload_time if upload_time > 0 else 0
                result["upload_speed"] = round(upload_speed, 2)

                # Download test
                start_time = time.time()
                with sftp.file(remote_path, "rb") as f:
                    f.read()
                download_time = time.time() - start_time
                download_speed = size / download_time if download_time > 0 else 0
                result["download_speed"] = round(download_speed, 2)

                # Cleanup
                sftp.remove(remote_path)
                sftp.close()

            except Exception as e:
                # SFTP not available, estimate speed from command execution
                self._log(f"SFTP not available, using command-based test: {e}", "debug")

                # Use echo to test data transfer
                start_time = time.time()
                stdin, stdout, stderr = ssh_client.exec_command(f"dd if=/dev/zero bs={size} count=1 2>/dev/null | wc -c")
                output = stdout.read()
                transfer_time = time.time() - start_time
                result["download_speed"] = round(size / transfer_time if transfer_time > 0 else 0, 2)
                result["upload_speed"] = result["download_speed"]  # Estimate

            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            self._log(f"Speed test error: {e}", "debug")

        return result

    def test_raw_socket(self, host: str, port: int) -> Dict:
        """
        Test raw socket connection speed.

        Args:
            host: Target host
            port: Target port

        Returns:
            Dictionary with test results
        """
        result = {
            "success": False,
            "connection_time_ms": 0.0,
            "latency_ms": 0.0,
            "error": None,
        }

        try:
            # Test connection time
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            connection_time = (time.time() - start_time) * 1000
            result["connection_time_ms"] = round(connection_time, 2)

            # Measure latency with minimal data
            test_data = b"\x00" * 64
            start_time = time.time()
            try:
                sock.send(test_data)
                # Don't wait for response as server may not echo
                latency = (time.time() - start_time) * 1000
                result["latency_ms"] = round(latency, 2)
            except Exception:
                pass

            sock.close()
            result["success"] = True

        except socket.timeout:
            result["error"] = "Connection timed out"
        except socket.error as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

        return result

    def measure_bandwidth(self, ssh_client, duration: int = 5) -> Dict:
        """
        Measure bandwidth over a period of time.

        Args:
            ssh_client: Paramiko SSH client
            duration: Test duration in seconds

        Returns:
            Dictionary with bandwidth metrics
        """
        result = {
            "success": False,
            "avg_speed": 0.0,
            "peak_speed": 0.0,
            "min_speed": float("inf"),
            "samples": [],
            "error": None,
        }

        try:
            # Open SFTP channel
            sftp = ssh_client.open_sftp()
            remote_path = "/tmp/.bandwidth_test_" + str(int(time.time()))

            chunk_size = 4096
            samples = []
            end_time = time.time() + duration

            while time.time() < end_time:
                data = b"X" * chunk_size
                start = time.time()
                with sftp.file(remote_path, "wb") as f:
                    f.write(data)
                elapsed = time.time() - start

                if elapsed > 0:
                    speed = chunk_size / elapsed
                    samples.append(speed)

                    if speed > result["peak_speed"]:
                        result["peak_speed"] = speed
                    if speed < result["min_speed"]:
                        result["min_speed"] = speed

            # Cleanup
            try:
                sftp.remove(remote_path)
            except Exception:
                pass
            sftp.close()

            if samples:
                result["avg_speed"] = round(sum(samples) / len(samples), 2)
                result["peak_speed"] = round(result["peak_speed"], 2)
                result["min_speed"] = round(result["min_speed"], 2)
                result["samples"] = len(samples)
                result["success"] = True
            else:
                result["min_speed"] = 0

        except Exception as e:
            result["error"] = str(e)
            result["min_speed"] = 0

        return result

    def is_acceptable_speed(self, speed: float) -> bool:
        """
        Check if speed meets minimum requirements.

        Args:
            speed: Speed in bytes/sec

        Returns:
            True if speed is acceptable
        """
        return speed >= self.min_speed

    def format_speed(self, speed: float) -> str:
        """
        Format speed in human-readable format.

        Args:
            speed: Speed in bytes/sec

        Returns:
            Formatted speed string
        """
        if speed >= 1024 * 1024:
            return f"{speed / (1024 * 1024):.2f} MB/s"
        elif speed >= 1024:
            return f"{speed / 1024:.2f} KB/s"
        else:
            return f"{speed:.2f} B/s"

    def test_tunnel_quality(self, ssh_client) -> Dict:
        """
        Comprehensive tunnel quality test.

        Args:
            ssh_client: Paramiko SSH client

        Returns:
            Dictionary with quality metrics
        """
        result = {
            "quality_score": 0,  # 0-100
            "latency": None,
            "speed": None,
            "stability": None,
            "recommendation": "",
        }

        # Test latency
        latency_test = self.test_ssh_connection(ssh_client, test_data_size=64)
        if latency_test["success"]:
            result["latency"] = latency_test["latency_ms"]

            # Score latency (lower is better)
            if latency_test["latency_ms"] < 50:
                result["quality_score"] += 40
            elif latency_test["latency_ms"] < 100:
                result["quality_score"] += 30
            elif latency_test["latency_ms"] < 200:
                result["quality_score"] += 20
            elif latency_test["latency_ms"] < 500:
                result["quality_score"] += 10

        # Test speed
        speed_test = self.test_ssh_connection(ssh_client, test_data_size=self.test_size)
        if speed_test["success"]:
            avg_speed = (speed_test["upload_speed"] + speed_test["download_speed"]) / 2
            result["speed"] = self.format_speed(avg_speed)

            # Score speed
            if avg_speed >= 1024 * 1024:  # 1 MB/s+
                result["quality_score"] += 40
            elif avg_speed >= 512 * 1024:  # 512 KB/s+
                result["quality_score"] += 30
            elif avg_speed >= 128 * 1024:  # 128 KB/s+
                result["quality_score"] += 20
            elif avg_speed >= 32 * 1024:  # 32 KB/s+
                result["quality_score"] += 10

        # Test stability (multiple quick tests)
        stability_samples = []
        for _ in range(3):
            test = self.test_ssh_connection(ssh_client, test_data_size=1024)
            if test["success"]:
                stability_samples.append(test["latency_ms"])

        if len(stability_samples) >= 2:
            variance = sum((x - sum(stability_samples) / len(stability_samples)) ** 2 
                          for x in stability_samples) / len(stability_samples)
            result["stability"] = f"Variance: {variance:.2f}ms"

            # Score stability (lower variance is better)
            if variance < 10:
                result["quality_score"] += 20
            elif variance < 50:
                result["quality_score"] += 15
            elif variance < 100:
                result["quality_score"] += 10

        # Generate recommendation
        if result["quality_score"] >= 80:
            result["recommendation"] = "Excellent connection quality"
        elif result["quality_score"] >= 60:
            result["recommendation"] = "Good connection quality"
        elif result["quality_score"] >= 40:
            result["recommendation"] = "Acceptable connection quality"
        elif result["quality_score"] >= 20:
            result["recommendation"] = "Poor connection quality - may experience issues"
        else:
            result["recommendation"] = "Very poor connection - not recommended"

        return result
