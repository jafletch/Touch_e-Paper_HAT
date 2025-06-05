#!/bin/bash

# Git File Monitor Script
# This script monitors a specific file in a git repository for changes and automatically pulls updates

# Configuration
REPO_DIR="/path/to/your/repository"          # Change this to your repository path
BRANCH="main"                                # Branch to monitor (change if needed)
MONITOR_FILE="python/examples/TP2in13_V4_test.py"  # Specific file to monitor
CHECK_INTERVAL=30                           # Check interval in seconds
LOG_FILE="/var/log/git-file-monitor.log"    # Log file path
RESTART_COMMAND="systemctl restart your-service"  # Command to restart your service
SCRIPT_NAME="$(basename "$0")"
PID_FILE="/tmp/git-file-monitor.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error logging function
log_error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# Success logging function
log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

# Warning logging function
log_warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S') - WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# Check if script is already running
check_if_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_error "Script is already running with PID $pid"
            exit 1
        else
            log_warning "Stale PID file found, removing it"
            rm -f "$PID_FILE"
        fi
    fi
}

# Create PID file
create_pid_file() {
    echo $$ > "$PID_FILE"
    log "Created PID file with PID $$"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    rm -f "$PID_FILE"
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGTERM SIGINT

# Validate configuration
validate_config() {
    if [ ! -d "$REPO_DIR" ]; then
        log_error "Repository directory $REPO_DIR does not exist"
        exit 1
    fi
    
    if [ ! -d "$REPO_DIR/.git" ]; then
        log_error "$REPO_DIR is not a git repository"
        exit 1
    fi
    
    if [ ! -f "$REPO_DIR/$MONITOR_FILE" ]; then
        log_error "Monitored file $REPO_DIR/$MONITOR_FILE does not exist"
        exit 1
    fi
    
    # Create log directory if it doesn't exist
    local log_dir=$(dirname "$LOG_FILE")
    if [ ! -d "$log_dir" ]; then
        mkdir -p "$log_dir" || {
            log_error "Cannot create log directory $log_dir"
            exit 1
        }
    fi
}

# Change to repository directory
change_to_repo() {
    cd "$REPO_DIR" || {
        log_error "Cannot change to repository directory $REPO_DIR"
        exit 1
    }
}

# Get current file hash from local repository
get_local_file_hash() {
    git rev-parse HEAD:"$MONITOR_FILE" 2>/dev/null
}

# Get file hash from remote repository
get_remote_file_hash() {
    git rev-parse "origin/$BRANCH":"$MONITOR_FILE" 2>/dev/null
}

# Check for changes to the specific file
check_file_changes() {
    # Fetch latest changes from remote
    git fetch origin "$BRANCH" 2>/dev/null || {
        log_error "Failed to fetch from remote"
        return 1
    }
    
    # Get local and remote file hashes
    local local_hash=$(get_local_file_hash)
    local remote_hash=$(get_remote_file_hash)
    
    if [ -z "$local_hash" ]; then
        log_error "Failed to get local file hash for $MONITOR_FILE"
        return 1
    fi
    
    if [ -z "$remote_hash" ]; then
        log_error "Failed to get remote file hash for $MONITOR_FILE"
        return 1
    fi
    
    if [ "$local_hash" != "$remote_hash" ]; then
        log "File changes detected for $MONITOR_FILE"
        log "Local hash: $local_hash"
        log "Remote hash: $remote_hash"
        return 0
    else
        return 1
    fi
}

# Get file modification details
get_file_changes() {
    local old_hash=$(get_local_file_hash)
    local new_hash=$(get_remote_file_hash)
    
    log "File change details for $MONITOR_FILE:"
    
    # Show the commits that changed this file
    git log --oneline --follow "$old_hash".."origin/$BRANCH" -- "$MONITOR_FILE" | head -5 | while read line; do
        log "  Commit: $line"
    done
    
    # Show file diff summary
    local diff_stats=$(git diff --stat "$old_hash" "origin/$BRANCH" -- "$MONITOR_FILE" 2>/dev/null)
    if [ -n "$diff_stats" ]; then
        log "  Changes: $diff_stats"
    fi
}

# Pull changes from remote
pull_changes() {
    log "Pulling changes from remote..."
    
    # Get file change details before pulling
    get_file_changes
    
    # Check if there are uncommitted changes to the monitored file
    if ! git diff-index --quiet HEAD -- "$MONITOR_FILE"; then
        log_warning "Uncommitted changes detected in $MONITOR_FILE, stashing them"
        git stash push -m "Auto-stash before pull $(date)" -- "$MONITOR_FILE" || {
            log_error "Failed to stash changes for $MONITOR_FILE"
            return 1
        }
    fi
    
    # Pull changes
    git pull origin "$BRANCH" || {
        log_error "Failed to pull changes"
        return 1
    }
    
    log_success "Successfully pulled changes for $MONITOR_FILE"
    return 0
}

# Restart service/application
restart_application() {
    if [ -n "$RESTART_COMMAND" ]; then
        log "Executing restart command: $RESTART_COMMAND"
        eval "$RESTART_COMMAND" || {
            log_error "Failed to restart application"
            return 1
        }
        log_success "Successfully restarted application"
    else
        log_warning "No restart command specified"
    fi
}

# Restart this script
restart_script() {
    log "Restarting monitoring script..."
    rm -f "$PID_FILE"
    exec "$0" "$@"
}

# Main monitoring loop
monitor_file() {
    log "Starting file monitoring..."
    log "Repository: $REPO_DIR"
    log "Branch: $BRANCH"
    log "Monitoring file: $MONITOR_FILE"
    log "Check interval: ${CHECK_INTERVAL}s"
    
    while true; do
        if check_file_changes; then
            if pull_changes; then
                restart_application
                
                # Optional: restart this script after pulling changes
                # Uncomment the next line if you want the script to restart itself
                # restart_script "$@"
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Show file status
show_file_status() {
    change_to_repo
    
    local local_hash=$(get_local_file_hash)
    local remote_hash=$(get_remote_file_hash)
    
    echo "File monitoring status for: $MONITOR_FILE"
    echo "Local file hash:  $local_hash"
    echo "Remote file hash: $remote_hash"
    
    if [ "$local_hash" = "$remote_hash" ]; then
        echo "Status: File is up to date"
    else
        echo "Status: File has changes available"
        
        # Show last few commits that affected this file
        echo ""
        echo "Recent commits affecting this file:"
        git log --oneline --follow -5 "origin/$BRANCH" -- "$MONITOR_FILE" 2>/dev/null || echo "  No commit history found"
    fi
}

# Help function
show_help() {
    cat << EOF
Git File Monitor Script

Usage: $0 [OPTIONS]

OPTIONS:
    -d, --dir PATH          Repository directory (default: $REPO_DIR)
    -f, --file PATH         File to monitor (default: $MONITOR_FILE)
    -b, --branch NAME       Branch to monitor (default: $BRANCH)
    -i, --interval SECONDS  Check interval (default: $CHECK_INTERVAL)
    -r, --restart CMD       Restart command
    -l, --log PATH          Log file path (default: $LOG_FILE)
    -h, --help              Show this help message
    --stop                  Stop running instance
    --status                Show status of running instance
    --file-status           Show status of monitored file

Examples:
    $0 -d /opt/myapp -f "src/main.py" -b main -i 60 -r "systemctl restart myapp"
    $0 --dir /home/user/project --file "config/settings.py" --interval 30
    $0 --file-status
    $0 --stop
    $0 --status
EOF
}

# Stop running instance
stop_instance() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping instance with PID $pid..."
            kill "$pid"
            sleep 2
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force killing instance..."
                kill -9 "$pid"
            fi
            rm -f "$PID_FILE"
            echo "Instance stopped"
        else
            echo "No running instance found (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        echo "No PID file found, no instance running"
    fi
}

# Show status
show_status() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Instance is running with PID $pid"
            echo "Repository: $REPO_DIR"
            echo "Monitoring file: $MONITOR_FILE"
            echo "Branch: $BRANCH"
            echo "Log file: $LOG_FILE"
        else
            echo "PID file exists but process is not running (stale PID file)"
        fi
    else
        echo "No instance running"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            REPO_DIR="$2"
            shift 2
            ;;
        -f|--file)
            MONITOR_FILE="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -i|--interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        -r|--restart)
            RESTART_COMMAND="$2"
            shift 2
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        --stop)
            stop_instance
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --file-status)
            validate_config
            change_to_repo
            show_file_status
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    check_if_running
    create_pid_file
    validate_config
    change_to_repo
    monitor_file
}

# Run main function
main "$@"