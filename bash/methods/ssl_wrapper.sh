#!/bin/bash
#
# SSL Wrapper Method
#
# SSH wrapped in SSL/TLS (stunnel-like) for bypassing restrictions.
#

source "$(dirname "${BASH_SOURCE[0]}")/../tunnel_tester.sh" 2>/dev/null || true

# Default local port for SSL tunnel
SSL_LOCAL_PORT=2222

# Test SSL connection
test_ssl_connection() {
    local host=$1
    local port=${2:-443}
    local timeout=${3:-10}
    
    local start_time=$(date +%s%3N)
    
    # Test SSL/TLS handshake
    local ssl_output
    ssl_output=$(echo "" | timeout "$timeout" openssl s_client \
        -connect "$host:$port" \
        -servername "$host" \
        -brief 2>&1)
    
    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))
    
    if echo "$ssl_output" | grep -qi "verification"; then
        echo "success:SSL handshake OK (${latency}ms)"
        return 0
    elif echo "$ssl_output" | grep -qi "connected"; then
        echo "success:SSL connected (${latency}ms)"
        return 0
    else
        local error_msg=$(echo "$ssl_output" | grep -i "error" | head -1)
        echo "failed:${error_msg:-SSL handshake failed}"
        return 1
    fi
}

# Get SSL certificate info
get_ssl_info() {
    local host=$1
    local port=${2:-443}
    local timeout=${3:-10}
    
    echo "SSL Certificate Information for $host:$port"
    echo "============================================"
    
    echo "" | timeout "$timeout" openssl s_client \
        -connect "$host:$port" \
        -servername "$host" 2>/dev/null | \
        openssl x509 -noout -subject -issuer -dates 2>/dev/null
}

# Create stunnel configuration
create_stunnel_config() {
    local host=$1
    local remote_port=${2:-443}
    local local_port=${3:-$SSL_LOCAL_PORT}
    local ssh_port=${4:-22}
    local config_file=${5:-"/tmp/stunnel_tunnel.conf"}
    
    cat > "$config_file" << EOF
; Stunnel configuration for SSH over SSL
pid = /tmp/stunnel_tunnel.pid
foreground = yes
debug = 5

[ssh-tunnel]
client = yes
accept = 127.0.0.1:$local_port
connect = $host:$remote_port
; Uncomment if server expects SSH on different port
; protocol = connect
; protocolHost = $host:$ssh_port
verifyChain = no
verifyPeer = no
EOF
    
    echo "$config_file"
}

# Start SSL tunnel using stunnel
start_ssl_tunnel() {
    local host=$1
    local remote_port=${2:-443}
    local local_port=${3:-$SSL_LOCAL_PORT}
    
    if ! command -v stunnel &> /dev/null; then
        echo "Error: stunnel is not installed"
        echo "Install with: sudo apt-get install stunnel4"
        return 1
    fi
    
    echo "Starting SSL tunnel..."
    echo "  Remote: $host:$remote_port"
    echo "  Local: 127.0.0.1:$local_port"
    
    # Create configuration
    local config_file
    config_file=$(create_stunnel_config "$host" "$remote_port" "$local_port")
    
    # Start stunnel in background
    stunnel "$config_file" &
    local pid=$!
    
    # Wait a moment for startup
    sleep 2
    
    if kill -0 "$pid" 2>/dev/null; then
        echo "SSL tunnel started (PID: $pid)"
        echo "Connect via: ssh -p $local_port user@127.0.0.1"
        echo "$pid"
        return 0
    else
        echo "Failed to start SSL tunnel"
        return 1
    fi
}

# Stop SSL tunnel
stop_ssl_tunnel() {
    local pid_file=${1:-"/tmp/stunnel_tunnel.pid"}
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "SSL tunnel stopped (PID: $pid)"
            rm -f "$pid_file"
            return 0
        fi
    fi
    
    # Try to find and kill any stunnel processes
    pkill -f "stunnel.*tunnel" 2>/dev/null
    echo "SSL tunnel stopped"
}

# Connect SSH over SSL tunnel
connect_ssl() {
    local host=$1
    local ssl_port=${2:-443}
    local user=$3
    local password=$4
    local key_file=$5
    local local_port=${6:-$SSL_LOCAL_PORT}
    
    # Start SSL tunnel
    local tunnel_pid
    tunnel_pid=$(start_ssl_tunnel "$host" "$ssl_port" "$local_port")
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Build SSH command
    local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    local ssh_cmd="ssh $ssh_opts -p $local_port"
    
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        ssh_cmd="$ssh_cmd -i $key_file"
    fi
    
    ssh_cmd="$ssh_cmd $user@127.0.0.1"
    
    echo "Connecting via SSL tunnel..."
    
    # Connect
    if [ -n "$password" ]; then
        if command -v sshpass &> /dev/null; then
            sshpass -p "$password" $ssh_cmd
        else
            $ssh_cmd
        fi
    else
        $ssh_cmd
    fi
    
    # Cleanup
    stop_ssl_tunnel
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        test)
            shift
            test_ssl_connection "$@"
            ;;
        info)
            shift
            get_ssl_info "$@"
            ;;
        start)
            shift
            start_ssl_tunnel "$@"
            ;;
        stop)
            shift
            stop_ssl_tunnel "$@"
            ;;
        connect)
            shift
            connect_ssl "$@"
            ;;
        *)
            echo "Usage: $0 {test|info|start|stop|connect} [options]"
            echo "  test HOST [PORT] [TIMEOUT]"
            echo "  info HOST [PORT] [TIMEOUT]"
            echo "  start HOST [REMOTE_PORT] [LOCAL_PORT]"
            echo "  stop [PID_FILE]"
            echo "  connect HOST SSL_PORT USER [PASSWORD] [KEY_FILE] [LOCAL_PORT]"
            exit 1
            ;;
    esac
fi
