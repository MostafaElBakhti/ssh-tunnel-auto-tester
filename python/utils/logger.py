"""
Logger Module - Colorized logging and output formatting for SSH Tunnel Tester
"""

import logging
import sys
from datetime import datetime
from typing import Optional

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class TunnelLogger:
    """
    Custom logger with colorized output for tunnel testing operations.
    """

    # Color codes for different log levels and statuses
    COLORS = {
        "success": Fore.GREEN if COLORAMA_AVAILABLE else "",
        "error": Fore.RED if COLORAMA_AVAILABLE else "",
        "warning": Fore.YELLOW if COLORAMA_AVAILABLE else "",
        "info": Fore.CYAN if COLORAMA_AVAILABLE else "",
        "testing": Fore.YELLOW if COLORAMA_AVAILABLE else "",
        "header": Fore.MAGENTA if COLORAMA_AVAILABLE else "",
        "reset": Style.RESET_ALL if COLORAMA_AVAILABLE else "",
        "bold": Style.BRIGHT if COLORAMA_AVAILABLE else "",
    }

    # Status symbols
    SYMBOLS = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
        "testing": "⋯",
        "arrow": "→",
        "bullet": "•",
    }

    def __init__(
        self,
        log_file: Optional[str] = None,
        level: str = "INFO",
        colorize: bool = True,
        verbose: bool = False,
        quiet: bool = False,
    ):
        """
        Initialize the tunnel logger.

        Args:
            log_file: Path to log file (optional)
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            colorize: Enable colored output
            verbose: Enable verbose output
            quiet: Suppress non-essential output
        """
        self.log_file = log_file
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.colorize = colorize and COLORAMA_AVAILABLE
        self.verbose = verbose
        self.quiet = quiet

        # Set up Python logging
        self.logger = logging.getLogger("TunnelTester")
        self.logger.setLevel(self.level)
        self.logger.handlers = []  # Clear existing handlers

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_format = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # File handler (if log file specified)
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)  # Log everything to file
            file_format = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

    def _colorize(self, text: str, color_key: str) -> str:
        """Apply color to text if colorization is enabled."""
        if self.colorize:
            return f"{self.COLORS.get(color_key, '')}{text}{self.COLORS['reset']}"
        return text

    def _format_message(self, message: str, status: str, prefix: Optional[str] = None) -> str:
        """Format a message with status symbol and optional prefix."""
        symbol = self.SYMBOLS.get(status, "")
        colored_symbol = self._colorize(symbol, status)

        if prefix:
            return f"{colored_symbol} [{prefix}] {message}"
        return f"{colored_symbol} {message}"

    def success(self, message: str, prefix: Optional[str] = None):
        """Log a success message (green)."""
        if not self.quiet:
            formatted = self._format_message(message, "success", prefix)
            colored_msg = self._colorize(formatted, "success")
            self.logger.info(colored_msg)

    def error(self, message: str, prefix: Optional[str] = None):
        """Log an error message (red)."""
        formatted = self._format_message(message, "error", prefix)
        colored_msg = self._colorize(formatted, "error")
        self.logger.error(colored_msg)

    def warning(self, message: str, prefix: Optional[str] = None):
        """Log a warning message (yellow)."""
        if not self.quiet:
            formatted = self._format_message(message, "warning", prefix)
            colored_msg = self._colorize(formatted, "warning")
            self.logger.warning(colored_msg)

    def info(self, message: str, prefix: Optional[str] = None):
        """Log an info message (cyan)."""
        if not self.quiet:
            formatted = self._format_message(message, "info", prefix)
            colored_msg = self._colorize(formatted, "info")
            self.logger.info(colored_msg)

    def testing(self, message: str, prefix: Optional[str] = None):
        """Log a testing/in-progress message (yellow)."""
        if not self.quiet:
            formatted = self._format_message(message, "testing", prefix)
            colored_msg = self._colorize(formatted, "testing")
            self.logger.info(colored_msg)

    def debug(self, message: str, prefix: Optional[str] = None):
        """Log a debug message (only in verbose mode)."""
        if self.verbose:
            formatted = self._format_message(message, "info", prefix)
            self.logger.debug(formatted)

    def header(self, title: str, width: int = 60):
        """Print a section header."""
        if not self.quiet:
            border = "=" * width
            padded_title = f" {title} ".center(width, "=")
            if self.colorize:
                border = self._colorize(border, "header")
                padded_title = self._colorize(padded_title, "header")
            print()
            print(border)
            print(padded_title)
            print(border)
            print()

    def subheader(self, title: str, width: int = 50):
        """Print a sub-section header."""
        if not self.quiet:
            border = "-" * width
            padded_title = f" {title} ".center(width, "-")
            if self.colorize:
                padded_title = self._colorize(padded_title, "info")
            print()
            print(padded_title)
            print()

    def result_line(self, method: str, status: str, details: str = ""):
        """Print a result line for a test method."""
        if self.quiet:
            return

        method_padded = method.ljust(20)
        if status == "success":
            status_text = self._colorize("[SUCCESS]", "success")
        elif status == "failed":
            status_text = self._colorize("[FAILED]", "error")
        elif status == "testing":
            status_text = self._colorize("[TESTING]", "testing")
        elif status == "skipped":
            status_text = self._colorize("[SKIPPED]", "warning")
        else:
            status_text = f"[{status.upper()}]"

        line = f"  {self.SYMBOLS['arrow']} {method_padded} {status_text}"
        if details:
            line += f" - {details}"
        print(line)

    def progress_bar(self, current: int, total: int, width: int = 40, prefix: str = ""):
        """Display a progress bar."""
        if self.quiet:
            return

        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percent = current / total * 100

        if self.colorize:
            bar = self._colorize(bar, "info")

        sys.stdout.write(f"\r{prefix}[{bar}] {percent:.1f}% ({current}/{total})")
        sys.stdout.flush()

        if current >= total:
            print()  # New line at completion

    def summary_table(self, results: list):
        """Print a summary table of test results."""
        if self.quiet:
            return

        self.subheader("Test Results Summary")

        # Count results
        success_count = sum(1 for r in results if r.get("status") == "success")
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        skipped_count = sum(1 for r in results if r.get("status") == "skipped")

        print(f"  Total Tests: {len(results)}")
        print(f"  {self._colorize(f'Success: {success_count}', 'success')}")
        print(f"  {self._colorize(f'Failed: {failed_count}', 'error')}")
        print(f"  {self._colorize(f'Skipped: {skipped_count}', 'warning')}")
        print()

        # Print individual results
        for result in results:
            method = result.get("method", "Unknown")
            status = result.get("status", "unknown")
            details = result.get("details", "")
            self.result_line(method, status, details)

    def banner(self):
        """Print the application banner."""
        if self.quiet:
            return

        banner_text = """
╔═══════════════════════════════════════════════════════════════╗
║           SSH Tunnel Auto-Tester v1.0.0                       ║
║   Automatic SSH tunneling through restricted networks         ║
╚═══════════════════════════════════════════════════════════════╝
"""
        if self.colorize:
            banner_text = self._colorize(banner_text, "header")
        print(banner_text)

    def timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_to_file(self, message: str, level: str = "INFO"):
        """Write a message directly to the log file."""
        if self.log_file:
            timestamp = self.timestamp()
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} - {level} - {message}\n")
