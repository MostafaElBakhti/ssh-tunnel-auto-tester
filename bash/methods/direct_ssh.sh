#!/bin/bash
#
# Direct SSH Connection Method
#
# Standard SSH connection without any tunneling or obfuscation.
#

source "$(dirname "${BASH_SOURCE[0]}")/../tunnel_tester.sh" 2>/dev/null || true

# Test direct SSH connection
test_direct_connection() {
    local host=$1
    local port=${2:-22}
    local user=$3
    local password=$4
    local key_file=$5
    local timeout=${6:-10}
    
    local start_time=$(date +%s%3N)
    local ssh_opts="-o ConnectTimeout=$timeout -o StrictHostKeyChecking=no -o BatchMode=yes -o UserKnownHostsFile=/dev/null"
    
    # Check if port is reachable
    if ! nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
        echo "failed:Port $port not reachable on $host"
        return 1
    fi
    
    # Build SSH command
    local ssh_cmd="ssh $ssh_opts -p $port"
    
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        ssh_cmd="$ssh_cmd -i $key_file"
    fi
    
    ssh_cmd="$ssh_cmd $user@$host"
    
    # Test connection
    local output
    if [ -n "$password" ]; then
        if command -v sshpass &> /dev/null; then
            output=$(sshpass -p "$password" $ssh_cmd "echo connected" 2>&1)
        else
            # Try without password - may use key or fail
            output=$($ssh_cmd "echo connected" 2>&1)
        fi
    else
        output=$($ssh_cmd "echo connected" 2>&1)
    fi
    
    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))
    
    if echo "$output" | grep -q "connected"; then
        echo "success:Connected in ${latency}ms"
        return 0
    else
        local error_msg=$(echo "$output" | head -1)
        echo "failed:$error_msg"
        return 1
    fi
}

# Connect and maintain SSH session
connect_direct() {
    local host=$1
    local port=${2:-22}
    local user=$3
    local password=$4
    local key_file=$5
    
    local ssh_opts="-o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=3"
    local ssh_cmd="ssh $ssh_opts -p $port"
    
    if [ -n "$key_file" ] && [ -f "$key_file" ]; then
        ssh_cmd="$ssh_cmd -i $key_file"
    fi
    
    ssh_cmd="$ssh_cmd $user@$host"
    
    echo "Connecting to $user@$host:$port..."
    
    if [ -n "$password" ]; then
        if command -v sshpass &> /dev/null; then
            sshpass -p "$password" $ssh_cmd
        else
            echo "Warning: sshpass not available, password authentication may fail"
            $ssh_cmd
        fi
    else
        $ssh_cmd
    fi
}

# Scan multiple ports
scan_ports() {
    local host=$1
    local ports=${2:-"22,80,443,8080,8443"}
    local timeout=${3:-2}
    
    echo "Scanning ports on $host..."
    
    IFS=',' read -ra port_list <<< "$ports"
    
    for port in "${port_list[@]}"; do
        if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
            echo "  Port $port: OPEN"
        else
            echo "  Port $port: CLOSED"
        fi
    done
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        test)
            shift
            test_direct_connection "$@"
            ;;
        connect)
            shift
            connect_direct "$@"
            ;;
        scan)
            shift
            scan_ports "$@"
            ;;
        *)
            echo "Usage: $0 {test|connect|scan} [options]"
            echo "  test HOST PORT USER [PASSWORD] [KEY_FILE] [TIMEOUT]"
            echo "  connect HOST PORT USER [PASSWORD] [KEY_FILE]"
            echo "  scan HOST [PORTS] [TIMEOUT]"
            exit 1
            ;;
    esac
fi
