#!/usr/bin/env python3
"""
SSH Tunnel Auto-Tester - Command Line Interface

A comprehensive SSH tunneling tool that automatically tests multiple methods
to establish connections through restricted networks.

Usage:
    python tunnel_tester.py --auto                    # Auto-test all methods
    python tunnel_tester.py --find-and-connect        # Find working method and connect
    python tunnel_tester.py --method direct --host example.com --user myuser
    python tunnel_tester.py --interactive             # Interactive menu mode

For more information, see: https://github.com/your-repo/ssh-tunnel-auto-tester
"""

import argparse
import getpass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from python.core import TunnelTester
    from python.utils.config_parser import ConfigParser, ConfigError
    from python.utils.logger import TunnelLogger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="tunnel_tester",
        description="SSH Tunnel Auto-Tester - Test multiple SSH tunneling methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --auto                           Auto-test all configured methods
  %(prog)s --config myconfig.yaml --auto    Use custom config file
  %(prog)s --find-and-connect               Find working method and connect
  %(prog)s --method direct --host srv.com   Test specific method
  %(prog)s --quick --host srv.com --user me Quick test with credentials
  %(prog)s --interactive                    Interactive menu mode
  %(prog)s --list-methods                   List available methods
  %(prog)s --export results.json            Export results to JSON

For more information, visit: https://github.com/your-repo/ssh-tunnel-auto-tester
        """,
    )

    # Configuration
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        metavar="FILE",
        help="Path to YAML configuration file (default: config.yaml)",
    )
    config_group.add_argument(
        "--create-config",
        action="store_true",
        help="Create example configuration file and exit",
    )

    # Connection options
    conn_group = parser.add_argument_group("Connection Options")
    conn_group.add_argument(
        "-H", "--host",
        metavar="HOST",
        help="SSH server hostname or IP address",
    )
    conn_group.add_argument(
        "-P", "--port",
        type=int,
        metavar="PORT",
        help="SSH server port (default: 22)",
    )
    conn_group.add_argument(
        "-u", "--user", "--username",
        dest="username",
        metavar="USER",
        help="SSH username",
    )
    conn_group.add_argument(
        "-p", "--password",
        metavar="PASS",
        help="SSH password (will prompt if not provided)",
    )
    conn_group.add_argument(
        "-k", "--key", "--key-file",
        dest="key_file",
        metavar="FILE",
        help="Path to SSH private key file",
    )

    # Test modes
    test_group = parser.add_argument_group("Test Modes")
    test_group.add_argument(
        "-a", "--auto",
        action="store_true",
        help="Automatically test all configured methods",
    )
    test_group.add_argument(
        "-m", "--method",
        metavar="METHOD",
        help="Test specific method (direct, websocket, ssl_wrap, http_tunnel, etc.)",
    )
    test_group.add_argument(
        "--ports",
        metavar="PORTS",
        help="Comma-separated list of ports to test (e.g., 22,80,443)",
    )
    test_group.add_argument(
        "-q", "--quick",
        action="store_true",
        help="Quick test mode - test direct connection only",
    )
    test_group.add_argument(
        "--find-and-connect",
        action="store_true",
        help="Find working method and establish connection",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    output_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )
    output_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    output_group.add_argument(
        "-e", "--export",
        metavar="FILE",
        help="Export results to file (JSON or CSV based on extension)",
    )
    output_group.add_argument(
        "-l", "--log",
        metavar="FILE",
        help="Log file path",
    )

    # Information
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "--list-methods",
        action="store_true",
        help="List available tunneling methods",
    )
    info_group.add_argument(
        "--detect-network",
        action="store_true",
        help="Detect and display network information",
    )
    info_group.add_argument(
        "--version",
        action="version",
        version="SSH Tunnel Auto-Tester v1.0.0",
    )

    # Interactive mode
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive menu mode",
    )

    return parser


def list_methods():
    """List available tunneling methods."""
    logger = TunnelLogger(colorize=True)
    logger.banner()
    logger.header("Available Tunneling Methods")

    methods = {
        "direct": ("Direct SSH", "Standard SSH connection"),
        "websocket": ("WebSocket Tunnel", "SSH over WebSocket protocol"),
        "ssl_wrap": ("SSL/TLS Wrapper", "SSH wrapped in SSL/TLS"),
        "http_tunnel": ("HTTP CONNECT Tunnel", "SSH through HTTP proxy"),
        "dns_tunnel": ("DNS Tunnel", "SSH through DNS queries"),
        "sni_spoof": ("SNI Spoofing", "SSL with spoofed SNI header"),
        "obfuscated": ("Traffic Obfuscation", "Obfuscated SSH traffic"),
    }

    # Check which methods are available
    try:
        tester = TunnelTester()
        available = tester.get_available_methods()
        unavailable = tester.get_unavailable_methods()
    except Exception:
        available = ["direct"]  # Direct SSH should always be available
        unavailable = {}

    for method_id, (name, description) in methods.items():
        if method_id in available:
            status = logger._colorize("[AVAILABLE]", "success")
        else:
            reason = unavailable.get(method_id, "Missing dependencies")
            status = logger._colorize(f"[UNAVAILABLE: {reason}]", "error")

        print(f"  {method_id.ljust(15)} {name.ljust(25)} {status}")
        print(f"  {' ' * 15} {description}")
        print()


def detect_network():
    """Detect and display network information."""
    logger = TunnelLogger(colorize=True)
    logger.banner()
    logger.header("Network Detection")

    try:
        tester = TunnelTester()
        network_info = tester.detect_network()

        print(f"  Network Type:      {network_info.get('type', 'Unknown')}")
        print(f"  Interface:         {network_info.get('interface', 'Unknown')}")
        print(f"  IP Address:        {network_info.get('ip_address', 'Unknown')}")
        print(f"  Public IP:         {network_info.get('public_ip', 'Unknown')}")
        print(f"  Gateway:           {network_info.get('gateway', 'Unknown')}")
        print(f"  Internet:          {'Connected' if network_info.get('internet_connected') else 'Disconnected'}")
        if network_info.get('internet_latency_ms'):
            print(f"  Latency:           {network_info.get('internet_latency_ms'):.0f}ms")
        print()

        print("  Network Flags:")
        print(f"    Mobile/4G:       {'Yes' if network_info.get('is_mobile') else 'No'}")
        print(f"    WiFi:            {'Yes' if network_info.get('is_wifi') else 'No'}")
        print(f"    Ethernet:        {'Yes' if network_info.get('is_ethernet') else 'No'}")

    except Exception as e:
        logger.error(f"Network detection failed: {e}")


def interactive_mode():
    """Run interactive menu mode."""
    logger = TunnelLogger(colorize=True)
    logger.banner()

    while True:
        print("\n" + "=" * 50)
        print("  SSH Tunnel Auto-Tester - Interactive Mode")
        print("=" * 50)
        print()
        print("  1. Auto-test all methods")
        print("  2. Test specific method")
        print("  3. Find and connect")
        print("  4. List available methods")
        print("  5. Detect network")
        print("  6. View configuration")
        print("  7. Exit")
        print()

        try:
            choice = input("  Select option (1-7): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if choice == "1":
            # Auto-test
            try:
                config_path = input("  Config file (Enter for default): ").strip()
                config_path = config_path if config_path else None

                tester = TunnelTester(config_path=config_path, verbose=True)
                tester.test_all_methods()
                tester.print_summary()
            except Exception as e:
                logger.error(f"Error: {e}")

        elif choice == "2":
            # Test specific method
            print("\n  Available methods: direct, websocket, ssl_wrap, http_tunnel, sni_spoof")
            method = input("  Method: ").strip()
            host = input("  Host: ").strip()
            username = input("  Username: ").strip()
            password = getpass.getpass("  Password: ")

            if method and host and username:
                account = {
                    "host": host,
                    "port": 22,
                    "username": username,
                    "password": password,
                }
                try:
                    tester = TunnelTester(verbose=True)
                    result = tester.test_method(method, account)
                    print(f"\n  Result: {result.get('status', 'unknown')}")
                    if result.get('error'):
                        print(f"  Error: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error: {e}")

        elif choice == "3":
            # Find and connect
            try:
                config_path = input("  Config file (Enter for default): ").strip()
                config_path = config_path if config_path else None

                tester = TunnelTester(config_path=config_path, verbose=True)
                if tester.find_and_connect():
                    print("\n  Connected! Press Ctrl+C to disconnect.")
                    try:
                        tester.keep_alive_loop()
                    except KeyboardInterrupt:
                        pass
                    finally:
                        tester.disconnect()
            except Exception as e:
                logger.error(f"Error: {e}")

        elif choice == "4":
            list_methods()

        elif choice == "5":
            detect_network()

        elif choice == "6":
            # View configuration
            config_path = input("  Config file (Enter for default): ").strip()
            try:
                config = ConfigParser(config_path if config_path else None)
                print("\n  Configuration:")
                print(f"    SSH Accounts: {len(config.get_ssh_accounts())}")
                print(f"    Test Modes: {config.get_test_modes()}")
                print(f"    Ports: {config.get_ports()}")
                print(f"    Timeout: {config.get_timeout()}s")
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        elif choice == "7":
            break

        else:
            print("  Invalid option, please try again.")


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle create-config
    if args.create_config:
        ConfigParser.create_example_config("config.yaml.example")
        print("Created config.yaml.example - copy to config.yaml and edit with your settings")
        return 0

    # Handle list-methods
    if args.list_methods:
        list_methods()
        return 0

    # Handle detect-network
    if args.detect_network:
        detect_network()
        return 0

    # Handle interactive mode
    if args.interactive:
        interactive_mode()
        return 0

    # Initialize logger for non-interactive modes
    logger = TunnelLogger(
        log_file=args.log,
        colorize=not args.no_color,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    # Load or create configuration
    try:
        if args.config:
            config = ConfigParser(args.config)
        else:
            # Try to load default config, use defaults if not found
            default_configs = ["config.yaml", "config.yml"]
            config = None
            for cfg_file in default_configs:
                if Path(cfg_file).exists():
                    config = ConfigParser(cfg_file)
                    break
            if config is None:
                config = ConfigParser()  # Use defaults
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Override config with command line arguments
    if args.verbose:
        config.set("verbose", True)
    if args.quiet:
        config.set("quiet", True)
    if not args.no_color:
        config.set("colorize", True)
    if args.log:
        config.set("log_file", args.log)

    # Build account from command line if provided
    cli_account = None
    if args.host and args.username:
        password = args.password
        if not password and not args.key_file:
            password = getpass.getpass("SSH Password: ")

        cli_account = {
            "host": args.host,
            "port": args.port or 22,
            "username": args.username,
            "password": password,
            "key_file": args.key_file,
        }

    # Parse ports if provided
    cli_ports = None
    if args.ports:
        try:
            cli_ports = [int(p.strip()) for p in args.ports.split(",")]
        except ValueError:
            logger.error("Invalid port format. Use comma-separated numbers (e.g., 22,80,443)")
            return 1

    # Create tester
    try:
        tester = TunnelTester(
            config=config,
            verbose=args.verbose,
            quiet=args.quiet,
        )
    except Exception as e:
        logger.error(f"Failed to initialize tester: {e}")
        return 1

    # Display banner
    if not args.quiet:
        logger.banner()

    # Execute requested action
    try:
        if args.find_and_connect:
            # Find and connect mode
            account = cli_account or (config.get_ssh_accounts()[0] if config.get_ssh_accounts() else None)
            if not account:
                logger.error("No SSH account configured. Use --host and --user or configure in config.yaml")
                return 1

            success = tester.find_and_connect(account)
            if success:
                logger.info("Press Ctrl+C to disconnect")
                try:
                    tester.keep_alive_loop()
                except KeyboardInterrupt:
                    pass
                finally:
                    tester.disconnect()
            return 0 if success else 1

        elif args.method:
            # Test specific method
            account = cli_account or (config.get_ssh_accounts()[0] if config.get_ssh_accounts() else None)
            if not account:
                logger.error("No SSH account configured. Use --host and --user or configure in config.yaml")
                return 1

            result = tester.test_method(args.method, account, cli_ports[0] if cli_ports else None)
            tester.results = [result]
            tester.print_summary()

            if args.export:
                tester.export_results(args.export)

            return 0 if result.get("status") == "success" else 1

        elif args.quick:
            # Quick test mode
            account = cli_account or (config.get_ssh_accounts()[0] if config.get_ssh_accounts() else None)
            if not account:
                logger.error("No SSH account configured. Use --host and --user or configure in config.yaml")
                return 1

            result = tester.test_method("direct", account)
            tester.results = [result]
            tester.print_summary()
            return 0 if result.get("status") == "success" else 1

        elif args.auto or (not args.interactive):
            # Auto-test mode (default if no other action specified)
            account = cli_account or (config.get_ssh_accounts()[0] if config.get_ssh_accounts() else None)

            if not account:
                logger.error("No SSH account configured. Use --host and --user or configure in config.yaml")
                logger.info("Create a config.yaml file with your SSH server details, or use command-line arguments:")
                logger.info("  python tunnel_tester.py --host your-server.com --user your_username --auto")
                return 1

            results = tester.test_all_methods(
                account=account,
                ports=cli_ports,
            )
            tester.print_summary()

            if args.export:
                tester.export_results(args.export)

            # Return success if at least one method worked
            success_count = sum(1 for r in results if r.get("status") == "success")
            return 0 if success_count > 0 else 1

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        tester.disconnect()
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
