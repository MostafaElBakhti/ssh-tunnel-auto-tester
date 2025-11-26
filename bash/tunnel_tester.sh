#!/bin/bash
#
# SSH Tunnel Auto-Tester - Bash Version
#
# A lightweight SSH tunneling tool that tests multiple methods
# to establish connections through restricted networks.
#
# Usage:
#   ./tunnel_tester.sh --auto                    # Auto-test all methods
#   ./tunnel_tester.sh --config config.yaml      # Use config file
#   ./tunnel_tester.sh --host example.com --user myuser --method direct
#
# Requirements:
#   - openssh-client
#   - stunnel4 (for SSL wrapper)
#   - corkscrew or proxytunnel (for HTTP tunneling)
#   - netcat-openbsd
#   - curl
#   - jq (for JSON parsing)
#

set -e

# Script info
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Symbols
SYMBOL_SUCCESS="✓"
SYMBOL_ERROR="✗"
SYMBOL_WARNING="⚠"
SYMBOL_INFO="ℹ"
SYMBOL_TESTING="⋯"

# Default configuration
DEFAULT_TIMEOUT=10
DEFAULT_RETRY_ATTEMPTS=3
DEFAULT_PORTS="22,80,443,8080,8443"
DEFAULT_METHODS="direct,ssl_wrap,http_tunnel"
LOG_FILE="tunnel_results.log"

# Global variables
CONFIG_FILE=""
SSH_HOST=""
SSH_PORT=22
SSH_USER=""
SSH_PASS=""
SSH_KEY=""
TIMEOUT=$DEFAULT_TIMEOUT
RETRY_ATTEMPTS=$DEFAULT_RETRY_ATTEMPTS
VERBOSE=false
QUIET=false
AUTO_MODE=false
TEST_METHOD=""
TEST_PORTS=""
EXPORT_FILE=""

# ============================================================================
# Utility Functions
# ============================================================================

log_info() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${CYAN}${SYMBOL_INFO}${NC} $1"
    fi
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log_success() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${GREEN}${SYMBOL_SUCCESS}${NC} $1"
    fi
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}${SYMBOL_ERROR}${NC} $1" >&2
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log_warning() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${YELLOW}${SYMBOL_WARNING}${NC} $1"
    fi
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log_testing() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${YELLOW}${SYMBOL_TESTING}${NC} $1"
    fi
}

log_debug() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
    echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

print_header() {
    if [ "$QUIET" != "true" ]; then
        echo
        echo -e "${MAGENTA}============================================================${NC}"
        echo -e "${MAGENTA}  $1${NC}"
        echo -e "${MAGENTA}============================================================${NC}"
        echo
    fi
}

print_banner() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${MAGENTA}"
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║           SSH Tunnel Auto-Tester v${VERSION} (Bash)               ║"
        echo "║   Automatic SSH tunneling through restricted networks         ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
}

result_line() {
    local method=$1
    local status=$2
    local details=$3
    
    if [ "$QUIET" = "true" ]; then
        return
    fi
    
    local padded_method=$(printf "%-20s" "$method")
    
    case $status in
        "success")
            echo -e "  → ${padded_method} ${GREEN}[SUCCESS]${NC} - $details"
            ;;
        "failed")
            echo -e "  → ${padded_method} ${RED}[FAILED]${NC} - $details"
            ;;
        "skipped")
            echo -e "  → ${padded_method} ${YELLOW}[SKIPPED]${NC} - $details"
            ;;
        *)
            echo -e "  → ${padded_method} [$status] - $details"
            ;;
    esac
}

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        return 1
    fi
    return 0
}

check_dependencies() {
    local missing=()
    
    # Required
    if ! check_command ssh; then
        missing+=("openssh-client")
    fi
    
    if ! check_command nc; then
        missing+=("netcat-openbsd")
    fi
    
    # Optional but recommended
    if ! check_command stunnel; then
        log_warning "stunnel not found - SSL wrapper method unavailable"
    fi
    
    if ! check_command corkscrew && ! check_command proxytunnel; then
        log_warning "corkscrew/proxytunnel not found - HTTP tunnel method limited"
    fi
    
    if ! check_command jq; then
        log_warning "jq not found - JSON export unavailable"
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing[*]}"
        log_info "Install with: sudo apt-get install ${missing[*]}"
        return 1
    fi
    
    return 0
}

# ============================================================================
# Configuration Functions
# ============================================================================

parse_yaml_simple() {
    # Simple YAML parser for basic config values
    local file=$1
    local key=$2
    
    if [ ! -f "$file" ]; then
        return
    fi
    
    grep "^${key}:" "$file" 2>/dev/null | sed "s/${key}:[[:space:]]*//" | tr -d '"' | tr -d "'"
}

load_config() {
    local config_file=$1
    
    if [ ! -f "$config_file" ]; then
        log_error "Config file not found: $config_file"
        return 1
    fi
    
    log_info "Loading configuration from $config_file"
    
    # Parse basic values (simple YAML parsing)
    local timeout_val=$(parse_yaml_simple "$config_file" "timeout")
    local retry_val=$(parse_yaml_simple "$config_file" "retry_attempts")
    local log_val=$(parse_yaml_simple "$config_file" "log_file")
    
    [ -n "$timeout_val" ] && TIMEOUT=$timeout_val
    [ -n "$retry_val" ] && RETRY_ATTEMPTS=$retry_val
    [ -n "$log_val" ] && LOG_FILE=$log_val
    
    # Try to extract first SSH account
    if check_command yq; then
        SSH_HOST=$(yq '.ssh_accounts[0].host' "$config_file" 2>/dev/null | tr -d '"')
        SSH_PORT=$(yq '.ssh_accounts[0].port' "$config_file" 2>/dev/null | tr -d '"')
        SSH_USER=$(yq '.ssh_accounts[0].username' "$config_file" 2>/dev/null | tr -d '"')
        SSH_KEY=$(yq '.ssh_accounts[0].key_file' "$config_file" 2>/dev/null | tr -d '"')
    fi
    
    return 0
}

# ============================================================================
# Test Methods
# ============================================================================

test_port_open() {
    local host=$1
    local port=$2
    local timeout=${3:-$TIMEOUT}
    
    log_debug "Testing port $port on $host"
    
    if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
        return 0
    fi
    return 1
}

test_direct_ssh() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local key=$5
    local timeout=${6:-$TIMEOUT}
    
    log_testing "Testing direct SSH to $host:$port"
    
    local start_time=$(date +%s%3N)
    local ssh_opts="-o ConnectTimeout=$timeout -o StrictHostKeyChecking=no -o BatchMode=yes"
    
    # First check if port is open
    if ! test_port_open "$host" "$port" "$timeout"; then
        echo "failed:Port $port not reachable"
        return 1
    fi
    
    # Build SSH command
    local ssh_cmd="ssh $ssh_opts -p $port"
    
    if [ -n "$key" ] && [ -f "$key" ]; then
        ssh_cmd="$ssh_cmd -i $key"
    fi
    
    ssh_cmd="$ssh_cmd $user@$host echo connected"
    
    # Test SSH connection
    local output
    if [ -n "$pass" ]; then
        # Use sshpass if available
        if check_command sshpass; then
            output=$(sshpass -p "$pass" $ssh_cmd 2>&1)
        else
            log_debug "sshpass not available, trying without password"
            output=$($ssh_cmd 2>&1)
        fi
    else
        output=$($ssh_cmd 2>&1)
    fi
    
    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))
    
    if echo "$output" | grep -q "connected"; then
        echo "success:Connected in ${latency}ms"
        return 0
    else
        echo "failed:${output}"
        return 1
    fi
}

test_ssl_wrap() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local key=$5
    local timeout=${6:-$TIMEOUT}
    
    log_testing "Testing SSL-wrapped connection to $host:$port"
    
    # Check if stunnel is available
    if ! check_command stunnel; then
        echo "skipped:stunnel not installed"
        return 2
    fi
    
    local start_time=$(date +%s%3N)
    
    # Test SSL connection
    local ssl_test
    ssl_test=$(echo | timeout "$timeout" openssl s_client -connect "$host:$port" -servername "$host" 2>&1)
    
    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))
    
    if echo "$ssl_test" | grep -q "BEGIN CERTIFICATE"; then
        # SSL handshake successful
        echo "success:SSL handshake OK (${latency}ms)"
        return 0
    else
        echo "failed:SSL handshake failed"
        return 1
    fi
}

test_http_tunnel() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local key=$5
    local timeout=${6:-$TIMEOUT}
    local proxy_host=${7:-$host}
    local proxy_port=${8:-$port}
    
    log_testing "Testing HTTP CONNECT tunnel through $proxy_host:$proxy_port"
    
    local start_time=$(date +%s%3N)
    
    # Test HTTP CONNECT
    local connect_request="CONNECT $host:22 HTTP/1.1\r\nHost: $host:22\r\n\r\n"
    local response
    response=$(echo -e "$connect_request" | timeout "$timeout" nc "$proxy_host" "$proxy_port" 2>&1 | head -1)
    
    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))
    
    if echo "$response" | grep -q "200"; then
        echo "success:HTTP CONNECT OK (${latency}ms)"
        return 0
    elif echo "$response" | grep -q "407"; then
        echo "failed:Proxy authentication required"
        return 1
    else
        echo "failed:HTTP CONNECT rejected"
        return 1
    fi
}

# ============================================================================
# Main Test Functions
# ============================================================================

run_single_test() {
    local method=$1
    local host=$2
    local port=$3
    local user=$4
    local pass=$5
    local key=$6
    
    case $method in
        "direct")
            test_direct_ssh "$host" "$port" "$user" "$pass" "$key"
            ;;
        "ssl_wrap")
            test_ssl_wrap "$host" "$port" "$user" "$pass" "$key"
            ;;
        "http_tunnel")
            test_http_tunnel "$host" "$port" "$user" "$pass" "$key"
            ;;
        *)
            echo "skipped:Unknown method"
            return 2
            ;;
    esac
}

run_auto_test() {
    print_header "Running Auto-Test"
    
    if [ -z "$SSH_HOST" ] || [ -z "$SSH_USER" ]; then
        log_error "SSH host and user required. Use --host and --user or config file."
        return 1
    fi
    
    log_info "Target: $SSH_HOST"
    log_info "User: $SSH_USER"
    
    # Parse methods and ports
    IFS=',' read -ra methods <<< "${TEST_METHOD:-$DEFAULT_METHODS}"
    IFS=',' read -ra ports <<< "${TEST_PORTS:-$DEFAULT_PORTS}"
    
    local total_tests=$((${#methods[@]} * ${#ports[@]}))
    local completed=0
    local success_count=0
    local results=()
    
    echo
    log_info "Testing ${#methods[@]} methods on ${#ports[@]} ports ($total_tests total tests)"
    echo
    
    for method in "${methods[@]}"; do
        for port in "${ports[@]}"; do
            local result
            result=$(run_single_test "$method" "$SSH_HOST" "$port" "$SSH_USER" "$SSH_PASS" "$SSH_KEY")
            
            local status="${result%%:*}"
            local details="${result#*:}"
            
            result_line "$method:$port" "$status" "$details"
            
            results+=("{\"method\":\"$method\",\"port\":$port,\"status\":\"$status\",\"details\":\"$details\"}")
            
            if [ "$status" = "success" ]; then
                ((success_count++))
            fi
            
            ((completed++))
        done
    done
    
    # Print summary
    echo
    print_header "Test Summary"
    log_info "Total: $total_tests | Success: $success_count | Failed: $((total_tests - success_count))"
    
    # Export results if requested
    if [ -n "$EXPORT_FILE" ]; then
        export_results "${results[@]}"
    fi
    
    return $((total_tests - success_count))
}

export_results() {
    local results=("$@")
    
    if ! check_command jq; then
        log_warning "jq not installed, cannot export JSON"
        return 1
    fi
    
    local json="["
    local first=true
    for result in "${results[@]}"; do
        if [ "$first" = "true" ]; then
            first=false
        else
            json+=","
        fi
        json+="$result"
    done
    json+="]"
    
    echo "$json" | jq '.' > "$EXPORT_FILE"
    log_success "Results exported to $EXPORT_FILE"
}

# ============================================================================
# Help and Usage
# ============================================================================

show_help() {
    cat << EOF
SSH Tunnel Auto-Tester v${VERSION} (Bash)

A lightweight SSH tunneling tool that tests multiple methods
to establish connections through restricted networks.

Usage:
    $(basename "$0") [OPTIONS]

Options:
    -c, --config FILE       Path to YAML configuration file
    -H, --host HOST         SSH server hostname or IP
    -P, --port PORT         SSH server port (default: 22)
    -u, --user USER         SSH username
    -p, --password PASS     SSH password
    -k, --key FILE          Path to SSH private key
    
    -a, --auto              Auto-test all methods
    -m, --method METHOD     Test specific method (direct, ssl_wrap, http_tunnel)
    --ports PORTS           Comma-separated ports to test
    
    -v, --verbose           Verbose output
    -q, --quiet             Quiet mode
    -e, --export FILE       Export results to JSON file
    -l, --log FILE          Log file path
    
    --list-methods          List available methods
    --check-deps            Check dependencies
    -h, --help              Show this help
    --version               Show version

Methods:
    direct      - Standard SSH connection
    ssl_wrap    - SSH wrapped in SSL/TLS
    http_tunnel - SSH through HTTP CONNECT proxy

Examples:
    # Auto-test with config file
    $(basename "$0") --config config.yaml --auto
    
    # Test direct connection
    $(basename "$0") --host example.com --user myuser --method direct
    
    # Test multiple ports
    $(basename "$0") --host example.com --user myuser --ports 22,80,443 --auto
    
    # Export results
    $(basename "$0") --config config.yaml --auto --export results.json

EOF
}

list_methods() {
    print_banner
    print_header "Available Tunneling Methods"
    
    echo "  Method          Description                    Status"
    echo "  ─────────────────────────────────────────────────────"
    
    # Direct SSH
    if check_command ssh; then
        echo -e "  direct          Standard SSH connection        ${GREEN}[AVAILABLE]${NC}"
    else
        echo -e "  direct          Standard SSH connection        ${RED}[UNAVAILABLE]${NC}"
    fi
    
    # SSL Wrapper
    if check_command stunnel; then
        echo -e "  ssl_wrap        SSH over SSL/TLS               ${GREEN}[AVAILABLE]${NC}"
    else
        echo -e "  ssl_wrap        SSH over SSL/TLS               ${YELLOW}[NEEDS stunnel]${NC}"
    fi
    
    # HTTP Tunnel
    if check_command nc; then
        echo -e "  http_tunnel     SSH through HTTP CONNECT       ${GREEN}[AVAILABLE]${NC}"
    else
        echo -e "  http_tunnel     SSH through HTTP CONNECT       ${RED}[NEEDS netcat]${NC}"
    fi
    
    echo
}

# ============================================================================
# Main
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -H|--host)
                SSH_HOST="$2"
                shift 2
                ;;
            -P|--port)
                SSH_PORT="$2"
                shift 2
                ;;
            -u|--user)
                SSH_USER="$2"
                shift 2
                ;;
            -p|--password)
                SSH_PASS="$2"
                shift 2
                ;;
            -k|--key)
                SSH_KEY="$2"
                shift 2
                ;;
            -a|--auto)
                AUTO_MODE=true
                shift
                ;;
            -m|--method)
                TEST_METHOD="$2"
                shift 2
                ;;
            --ports)
                TEST_PORTS="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -e|--export)
                EXPORT_FILE="$2"
                shift 2
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            --list-methods)
                list_methods
                exit 0
                ;;
            --check-deps)
                check_dependencies
                exit $?
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                echo "SSH Tunnel Auto-Tester v${VERSION} (Bash)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Print banner
    print_banner
    
    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi
    
    # Load config if specified
    if [ -n "$CONFIG_FILE" ]; then
        load_config "$CONFIG_FILE" || exit 1
    fi
    
    # Run appropriate mode
    if [ "$AUTO_MODE" = "true" ] || [ -n "$TEST_METHOD" ]; then
        run_auto_test
        exit $?
    else
        show_help
        exit 0
    fi
}

# Run main function
main "$@"
