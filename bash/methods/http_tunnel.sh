#!/bin/bash
#
# HTTP Tunnel Method
#
# SSH through HTTP CONNECT proxy for bypassing restrictions.
#

source "$(dirname "${BASH_SOURCE[0]}")/../tunnel_tester.sh" 2>/dev/null || true

# Test HTTP CONNECT capability
test_http_connect() {
    local proxy_host=$1
    local proxy_port=${2:-8080}
    local target_host=${3:-"www.google.com"}
    local target_port=${4:-443}
    local timeout=${5:-10}
    
    local start_time=$(date +%s%3N)
    
    # Send HTTP CONNECT request
    local connect_request="CONNECT ${target_host}:${target_port} HTTP/1.1\r\nHost: ${target_host}:${target_port}\r\n\r\n"
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
    elif echo "$response" | grep -q "403"; then
        echo "failed:CONNECT method forbidden"
        return 1
    elif [ -z "$response" ]; then
        echo "failed:No response from proxy"
        return 1
    else
        local status_code=$(echo "$response" | grep -oE "HTTP/[0-9.]+ [0-9]+" | awk '{print $2}')
        echo "failed:HTTP ${status_code:-error}"
        return 1
    fi
}

# Create SSH over HTTP tunnel using corkscrew
connect_via_corkscrew() {
    local ssh_host=$1
    local ssh_port=${2:-22}
    local ssh_user=$3
    local password=$4
    local key_file=$5
    local proxy_host=$6
    local proxy_port=${7:-8080}
    local proxy_user=$8
    local proxy_pass=$9
    
    if ! command -v corkscrew &> /dev/null; then
        echo "Error: corkscrew is not installed"
        echo "Install with: sudo apt-get install corkscrew"
        return 1
    fi
    
    # Create proxy auth file if needed
    local auth_file=""
    if [ -n "$proxy_user" ] && [ -n "$proxy_pass" ]; then
        auth_file="/tmp/.http_proxy_auth"
        echo "$proxy_user:$proxy_pass" > "$auth_file"
        chmod 600 "$auth_file"
    fi
    
    # Build SSH command with ProxyCommand
    local proxy_cmd="corkscrew $proxy_host $proxy_port %h %p"
    if [ -n "$auth_file" ]; then
        proxy_cmd="$proxy_cmd $auth_file"
    fi
    
    local ssh_opts="-o StrictHostKeyChecking=no -o ProxyCommand=\"$proxy_cmd\""
    local ssh_cmd="ssh $ssh_opts -p $ssh_port"
    
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        ssh_cmd="$ssh_cmd -i $key_file"
    fi
    
    ssh_cmd="$ssh_cmd $ssh_user@$ssh_host"
    
    echo "Connecting via HTTP proxy..."
    echo "  Proxy: $proxy_host:$proxy_port"
    echo "  Target: $ssh_user@$ssh_host:$ssh_port"
    
    if [ -n "$password" ]; then
        if command -v sshpass &> /dev/null; then
            eval "sshpass -p '$password' $ssh_cmd"
        else
            eval "$ssh_cmd"
        fi
    else
        eval "$ssh_cmd"
    fi
    
    # Cleanup
    [ -f "$auth_file" ] && rm -f "$auth_file"
}

# Create SSH over HTTP tunnel using proxytunnel
connect_via_proxytunnel() {
    local ssh_host=$1
    local ssh_port=${2:-22}
    local ssh_user=$3
    local password=$4
    local key_file=$5
    local proxy_host=$6
    local proxy_port=${7:-8080}
    local proxy_user=$8
    local proxy_pass=$9
    
    if ! command -v proxytunnel &> /dev/null; then
        echo "Error: proxytunnel is not installed"
        echo "Install with: sudo apt-get install proxytunnel"
        return 1
    fi
    
    # Build ProxyCommand
    local proxy_cmd="proxytunnel -p $proxy_host:$proxy_port -d $ssh_host:$ssh_port"
    if [ -n "$proxy_user" ]; then
        proxy_cmd="$proxy_cmd -P $proxy_user:$proxy_pass"
    fi
    
    local ssh_opts="-o StrictHostKeyChecking=no -o ProxyCommand=\"$proxy_cmd\""
    local ssh_cmd="ssh $ssh_opts"
    
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        ssh_cmd="$ssh_cmd -i $key_file"
    fi
    
    ssh_cmd="$ssh_cmd $ssh_user@$ssh_host"
    
    echo "Connecting via HTTP proxy (proxytunnel)..."
    echo "  Proxy: $proxy_host:$proxy_port"
    echo "  Target: $ssh_user@$ssh_host:$ssh_port"
    
    if [ -n "$password" ]; then
        if command -v sshpass &> /dev/null; then
            eval "sshpass -p '$password' $ssh_cmd"
        else
            eval "$ssh_cmd"
        fi
    else
        eval "$ssh_cmd"
    fi
}

# Auto-select best available HTTP tunnel method
connect_http_tunnel() {
    local ssh_host=$1
    local ssh_port=$2
    local ssh_user=$3
    local password=$4
    local key_file=$5
    local proxy_host=$6
    local proxy_port=$7
    local proxy_user=$8
    local proxy_pass=$9
    
    if command -v proxytunnel &> /dev/null; then
        connect_via_proxytunnel "$@"
    elif command -v corkscrew &> /dev/null; then
        connect_via_corkscrew "$@"
    else
        echo "Error: No HTTP tunneling tool available"
        echo "Install one of:"
        echo "  sudo apt-get install corkscrew"
        echo "  sudo apt-get install proxytunnel"
        return 1
    fi
}

# Find HTTP proxies on common ports
find_http_proxies() {
    local host=${1:-"127.0.0.1"}
    local ports=${2:-"8080,3128,8888,1080,8118"}
    local timeout=${3:-2}
    
    echo "Scanning for HTTP proxies on $host..."
    
    IFS=',' read -ra port_list <<< "$ports"
    local found_proxies=()
    
    for port in "${port_list[@]}"; do
        # Check if port is open
        if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
            # Try HTTP CONNECT
            local result
            result=$(test_http_connect "$host" "$port" "www.google.com" 443 "$timeout")
            local status="${result%%:*}"
            
            if [ "$status" = "success" ]; then
                echo "  Found HTTP proxy: $host:$port"
                found_proxies+=("$host:$port")
            fi
        fi
    done
    
    if [ ${#found_proxies[@]} -eq 0 ]; then
        echo "  No HTTP proxies found"
        return 1
    fi
    
    echo
    echo "Available proxies:"
    for proxy in "${found_proxies[@]}"; do
        echo "  $proxy"
    done
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        test)
            shift
            test_http_connect "$@"
            ;;
        connect)
            shift
            connect_http_tunnel "$@"
            ;;
        find)
            shift
            find_http_proxies "$@"
            ;;
        *)
            echo "Usage: $0 {test|connect|find} [options]"
            echo ""
            echo "Commands:"
            echo "  test PROXY_HOST [PROXY_PORT] [TARGET_HOST] [TARGET_PORT] [TIMEOUT]"
            echo "    Test HTTP CONNECT capability of a proxy"
            echo ""
            echo "  connect SSH_HOST SSH_PORT SSH_USER [PASSWORD] [KEY_FILE] PROXY_HOST [PROXY_PORT] [PROXY_USER] [PROXY_PASS]"
            echo "    Connect to SSH server through HTTP proxy"
            echo ""
            echo "  find [HOST] [PORTS] [TIMEOUT]"
            echo "    Find HTTP proxies on common ports"
            echo ""
            echo "Examples:"
            echo "  $0 test 192.168.1.1 8080"
            echo "  $0 connect ssh.example.com 22 myuser '' '' proxy.local 8080"
            echo "  $0 find 127.0.0.1"
            exit 1
            ;;
    esac
fi
