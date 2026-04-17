#!/bin/bash

# ============================================================
#   Audiobooker - Start All Services
#   • Skips services already running on their port
#   • Opens each service in its own bash terminal window
#   • Python services: venv setup + clean install + run
#   • Frontend: npm install + npm run dev
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="/tmp/audiobooker_launchers"
mkdir -p "$TMP_DIR"

# Detect git-bash.exe from the Git for Windows installation
GIT_BASH="$(cygpath -u "$PROGRAMFILES")/Git/git-bash.exe"
[ ! -f "$GIT_BASH" ] && GIT_BASH="$(cygpath -u "${PROGRAMFILES(X86)}")/Git/git-bash.exe"
[ ! -f "$GIT_BASH" ] && GIT_BASH="$(dirname "$(dirname "$(which bash)")")/../git-bash.exe"
if [ ! -f "$GIT_BASH" ]; then
    echo "ERROR: git-bash.exe not found. Ensure Git for Windows is installed."
    exit 1
fi

# ── Colours ──────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# ================================================================
#  SERVICE REGISTRY  — "Name|abs-path|port|type(python|node)"
#  Edit ports here if your .env differs.
# ================================================================
SERVICES=(
    "Frontend|${ROOT_DIR}/frontend|5173|node"
    "API Proxy|${ROOT_DIR}/api_proxy|8000|python"
    "Auth Service|${ROOT_DIR}/microservices/auth-service|8003|python"
    "Backend Service|${ROOT_DIR}/microservices/backend|8002|python"
    "Payment Service|${ROOT_DIR}/microservices/payment-service|8004|python"
    "PDF Processor|${ROOT_DIR}/microservices/pdf-processor|8001|python"
    "TTS Infrastructure|${ROOT_DIR}/microservices/tts-infrastructure|8005|python"
)

# ── Service field helpers ────────────────────────────────────────
svc_name() { echo "$1" | cut -d'|' -f1; }
svc_path() { echo "$1" | cut -d'|' -f2; }
svc_port() { echo "$1" | cut -d'|' -f3; }
svc_type() { echo "$1" | cut -d'|' -f4; }

# ── Port / process helpers ───────────────────────────────────────
is_port_in_use() {
    netstat -aon 2>/dev/null | grep -qE "[.:]${1}[[:space:]].*LISTENING"
}

get_pid_on_port() {
    netstat -aon 2>/dev/null \
        | grep -E "[.:]${1}[[:space:]].*LISTENING" \
        | awk '{print $NF}' \
        | head -1
}

kill_port() {
    local pid
    pid=$(get_pid_on_port "$1")
    if [ -n "$pid" ] && [ "$pid" != "0" ]; then
        taskkill //PID "$pid" //F > /dev/null 2>&1
        return 0
    fi
    return 1
}

# ================================================================
#  LAUNCHER SCRIPT BUILDERS
# ================================================================

make_python_script() {
    local name="$1" svc_path="$2" port="$3"
    local script_file="${TMP_DIR}/$(echo "$name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]').sh"

    cat > "$script_file" <<SCRIPT
#!/bin/bash
set +e
echo ""
echo "======================================"
echo "  ${name}  |  port ${port}"
echo "======================================"
echo ""

cd "${svc_path}" || { echo "ERROR: cannot cd to ${svc_path}"; exec bash; }

# ── Resolve venv ─────────────────────────────────────────────────
VENV_DIR=""
if   [ -d "venv" ];  then VENV_DIR="venv"
elif [ -d ".venv" ]; then VENV_DIR=".venv"
fi

# ── Create venv if missing ───────────────────────────────────────
if [ -z "\$VENV_DIR" ]; then
    echo "[setup] No venv found — creating venv/ with py..."
    py -m venv venv || {
        echo "ERROR: 'py' launcher not found. Is Python installed?"
        exec bash
    }
    VENV_DIR="venv"
else
    echo "[setup] Found existing venv: \$VENV_DIR"
fi

# ── Activate ─────────────────────────────────────────────────────
if   [ -f "\${VENV_DIR}/Scripts/activate" ]; then
    source "\${VENV_DIR}/Scripts/activate"
elif [ -f "\${VENV_DIR}/bin/activate" ]; then
    source "\${VENV_DIR}/bin/activate"
else
    echo "ERROR: activate script not found in \${VENV_DIR}"
    exec bash
fi

echo "[setup] Python : \$(which python)"
echo "[setup] Pip    : \$(which pip)"
echo ""

# ── Install deps ─────────────────────────────────────────────────
echo "[deps] Upgrading pip..."
pip install --upgrade pip -q
echo "[deps] Installing requirements.txt (prefer pre-built wheels)..."
if ! pip install --prefer-binary -r requirements.txt; then
    echo ""
    echo "[deps] WARNING: Some packages failed. Retrying with --no-build-isolation..."
    pip install --prefer-binary --no-build-isolation -r requirements.txt
fi
echo ""

# ── Run ──────────────────────────────────────────────────────────
echo "[run] Starting ${name}..."
echo ""
python main.py

echo ""
echo "[${name}] Process exited. Window stays open."
exec bash
SCRIPT

    echo "$script_file"
}

make_node_script() {
    local name="$1" svc_path="$2" port="$3"
    local script_file="${TMP_DIR}/$(echo "$name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]').sh"

    cat > "$script_file" <<SCRIPT
#!/bin/bash
set +e
echo ""
echo "======================================"
echo "  ${name}  |  port ${port}"
echo "======================================"
echo ""

cd "${svc_path}" || { echo "ERROR: cannot cd to ${svc_path}"; exec bash; }

if ! command -v npm &>/dev/null; then
    echo "ERROR: npm not found. Install Node.js and ensure it is in PATH."
    exec bash
fi

echo "[deps] Running npm install..."
npm install
echo ""
echo "[run] Starting Vite dev server..."
echo ""
npm run dev

echo ""
echo "[${name}] Process exited. Window stays open."
exec bash
SCRIPT

    echo "$script_file"
}

# ================================================================
#  LAUNCH A SERVICE
#   force=true  → skip the "already running" check
# ================================================================
launch_service() {
    local name="$1" svc_path="$2" port="$3" type="$4" force="${5:-false}"

    if [ "$force" != "true" ] && is_port_in_use "$port"; then
        echo -e "  ${YELLOW}[skip]    ${name} — already running on port ${port}${NC}"
        return 1
    fi

    local script_file
    if [ "$type" = "node" ]; then
        script_file=$(make_node_script   "$name" "$svc_path" "$port")
    else
        script_file=$(make_python_script "$name" "$svc_path" "$port")
    fi

    chmod +x "$script_file"
    "$GIT_BASH" "$script_file" &
    echo -e "  ${GREEN}[launched] ${name} (port ${port})${NC}"
    return 0
}

# ================================================================
#  STATUS DISPLAY
# ================================================================
show_status() {
    echo ""
    echo -e "${BOLD}  Service Status:${NC}"
    echo "  ──────────────────────────────────────────────────"
    local i=1
    for svc in "${SERVICES[@]}"; do
        local name port
        name=$(svc_name "$svc")
        port=$(svc_port "$svc")
        if is_port_in_use "$port"; then
            printf "  ${GREEN}%s) ● RUNNING${NC}  %s  (port %s)\n" "$i" "$name" "$port"
        else
            printf "  ${RED}%s) ○ STOPPED${NC}  %s  (port %s)\n" "$i" "$name" "$port"
        fi
        ((i++))
    done
    echo "  ──────────────────────────────────────────────────"
}

# ================================================================
#  MAIN — launch pass
# ================================================================
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║       Audiobooker — Starting All Services    ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

for svc in "${SERVICES[@]}"; do
    launch_service "$(svc_name "$svc")" "$(svc_path "$svc")" "$(svc_port "$svc")" "$(svc_type "$svc")"
    sleep 0.3
done

# ================================================================
#  MANAGER MENU
# ================================================================
show_status
echo ""
echo -e "${CYAN}${BOLD}  Audiobooker Service Manager${NC}"
echo "  Enter a number to manage a service."
echo "  [s] Refresh status   [r] Restart all   [x] Exit"
echo ""

while true; do
    echo -n "  > "
    read -r choice

    case "$choice" in
        s|S)
            show_status
            echo ""
            ;;
        r|R)
            echo ""
            echo -e "${YELLOW}  Restarting all services...${NC}"
            for svc in "${SERVICES[@]}"; do
                name=$(svc_name "$svc"); path=$(svc_path "$svc")
                port=$(svc_port "$svc"); type=$(svc_type "$svc")
                echo -e "  ${YELLOW}Stopping ${name}...${NC}"
                kill_port "$port"
                sleep 0.4
                launch_service "$name" "$path" "$port" "$type" "true"
                sleep 0.3
            done
            echo ""
            ;;
        x|X|q|Q)
            echo ""
            echo -e "${GREEN}  Exiting. Services continue running in their windows.${NC}"
            echo ""
            break
            ;;
        [1-9])
            idx=$((choice - 1))
            if [ "$idx" -lt "${#SERVICES[@]}" ]; then
                svc="${SERVICES[$idx]}"
                name=$(svc_name "$svc"); path=$(svc_path "$svc")
                port=$(svc_port "$svc"); type=$(svc_type "$svc")
                echo ""
                echo -e "  ${BOLD}${name}${NC}  (port ${port})"
                echo "  [1] Start   [2] Stop   [3] Restart   [b] Back"
                echo -n "  > "
                read -r action
                case "$action" in
                    1)
                        if is_port_in_use "$port"; then
                            echo -e "  ${YELLOW}Already running. Use [3] to restart.${NC}"
                        else
                            launch_service "$name" "$path" "$port" "$type" "true"
                        fi
                        ;;
                    2)
                        if kill_port "$port"; then
                            echo -e "  ${GREEN}Stopped.${NC}"
                        else
                            echo -e "  ${RED}Not running or could not stop.${NC}"
                        fi
                        ;;
                    3)
                        echo -e "  ${YELLOW}Stopping ${name}...${NC}"
                        kill_port "$port"; sleep 1
                        launch_service "$name" "$path" "$port" "$type" "true"
                        ;;
                    b|B) ;;
                    *) echo "  Invalid option." ;;
                esac
                echo ""
            else
                echo "  Invalid selection."
            fi
            ;;
        "")
            # blank enter — do nothing, re-show prompt
            ;;
        *)
            echo "  Unknown option: '$choice'"
            ;;
    esac
done
