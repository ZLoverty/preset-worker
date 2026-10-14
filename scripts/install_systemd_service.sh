#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DEFAULT_PROJECT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)

PROJECT_DIR=${DEFAULT_PROJECT_DIR}
SERVICE_NAME="preset-worker"
SERVICE_USER=""
SERVICE_GROUP=""
ENV_FILE=""
VENV_DIR=""
PYTHON_BIN="python3"
SKIP_INSTALL=0
ENABLE_SERVICE=0
START_SERVICE=0

usage() {
    cat <<'EOF'
Usage: install_systemd_service.sh [options]

Install or update a systemd service for `preset-worker run`.

Options:
  --project-dir DIR   Repository directory (default: repository root)
  --service-name NAME systemd unit name (default: preset-worker)
  --user USER         Service user (default: invoking user)
  --group GROUP       Service group (default: user's primary group)
  --env-file FILE     Worker .env file (default: PROJECT_DIR/.env)
  --venv-dir DIR      Python virtual environment (default: PROJECT_DIR/.venv)
  --python PATH       Python executable used to create the venv (default: python3)
  --skip-install      Do not run `pip install -e PROJECT_DIR`
  --enable            Enable the service at boot
  --start             Start/restart the service after installation
  -h, --help          Show this help

The script must be run as root (for example: sudo ...). When invoked through
sudo, the service defaults to the original invoking user. It does not create
or modify the worker .env file.
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)
            [[ $# -ge 2 ]] || die "--project-dir requires a value"
            PROJECT_DIR=$2
            shift 2
            ;;
        --service-name)
            [[ $# -ge 2 ]] || die "--service-name requires a value"
            SERVICE_NAME=$2
            shift 2
            ;;
        --user)
            [[ $# -ge 2 ]] || die "--user requires a value"
            SERVICE_USER=$2
            shift 2
            ;;
        --group)
            [[ $# -ge 2 ]] || die "--group requires a value"
            SERVICE_GROUP=$2
            shift 2
            ;;
        --env-file)
            [[ $# -ge 2 ]] || die "--env-file requires a value"
            ENV_FILE=$2
            shift 2
            ;;
        --venv-dir)
            [[ $# -ge 2 ]] || die "--venv-dir requires a value"
            VENV_DIR=$2
            shift 2
            ;;
        --python)
            [[ $# -ge 2 ]] || die "--python requires a value"
            PYTHON_BIN=$2
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=1
            shift
            ;;
        --enable)
            ENABLE_SERVICE=1
            shift
            ;;
        --start)
            ENABLE_SERVICE=1
            START_SERVICE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1 (use --help for usage)"
            ;;
    esac
done

[[ ${EUID} -eq 0 ]] || die "run this script as root, for example: sudo $0"

require_command systemctl
require_command install
require_command id
require_command getent
require_command runuser
require_command stat
require_command "$PYTHON_BIN"

PROJECT_DIR=$(cd -- "$PROJECT_DIR" 2>/dev/null && pwd) || die "project directory does not exist"
[[ -f "$PROJECT_DIR/pyproject.toml" ]] || die "pyproject.toml not found in $PROJECT_DIR"

if [[ -z "$SERVICE_USER" ]]; then
    SERVICE_USER=${SUDO_USER:-}
    if [[ -z "$SERVICE_USER" || "$SERVICE_USER" == "root" ]]; then
        SERVICE_USER=$(stat -c '%U' "$PROJECT_DIR")
    fi
    [[ -n "$SERVICE_USER" && "$SERVICE_USER" != "root" ]] \
        || die "cannot determine a non-root service user; pass --user USER explicitly"
fi
if [[ -z "$SERVICE_GROUP" ]]; then
    SERVICE_GROUP=$(id -gn "$SERVICE_USER") \
        || die "cannot determine primary group for service user: $SERVICE_USER"
fi
if [[ -z "$ENV_FILE" ]]; then
    ENV_FILE="$PROJECT_DIR/.env"
fi
if [[ -z "$VENV_DIR" ]]; then
    VENV_DIR="$PROJECT_DIR/.venv"
fi

ENV_FILE=$(readlink -f -- "$ENV_FILE" 2>/dev/null || true)
[[ -n "$ENV_FILE" && -f "$ENV_FILE" ]] || die ".env file not found: ${ENV_FILE:-unset}"

id "$SERVICE_USER" >/dev/null 2>&1 || die "service user does not exist: $SERVICE_USER"
getent group "$SERVICE_GROUP" >/dev/null 2>&1 || die "service group does not exist: $SERVICE_GROUP"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "creating virtual environment: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
    echo "installing preset-worker from: $PROJECT_DIR"
    "$VENV_DIR/bin/python" -m pip install --editable "$PROJECT_DIR"
fi

[[ -x "$VENV_DIR/bin/preset-worker" ]] || die "preset-worker executable not found in $VENV_DIR/bin"

runuser -u "$SERVICE_USER" -- test -x "$PROJECT_DIR" \
    || die "service user '$SERVICE_USER' cannot access project directory '$PROJECT_DIR'; use --user with an account that can traverse its parent directories, or deploy under /opt"
runuser -u "$SERVICE_USER" -- test -r "$ENV_FILE" \
    || die "service user '$SERVICE_USER' cannot read env file '$ENV_FILE'"
runuser -u "$SERVICE_USER" -- test -x "$VENV_DIR/bin/preset-worker" \
    || die "service user '$SERVICE_USER' cannot execute '$VENV_DIR/bin/preset-worker'"

install -d -m 0755 /etc/systemd/system
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
UNIT_TMP=$(mktemp "/etc/systemd/system/.${SERVICE_NAME}.service.XXXXXX")
trap 'rm -f -- "$UNIT_TMP"' EXIT

cat >"$UNIT_TMP" <<EOF
[Unit]
Description=preset-worker background worker
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_DIR/bin/preset-worker --env $ENV_FILE run
Restart=on-failure
RestartSec=10s
TimeoutStopSec=30s
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

chmod 0644 "$UNIT_TMP"
mv -- "$UNIT_TMP" "$UNIT_PATH"
trap - EXIT

systemctl daemon-reload
if [[ "$ENABLE_SERVICE" -eq 1 ]]; then
    systemctl enable "$SERVICE_NAME.service"
fi
if [[ "$START_SERVICE" -eq 1 ]]; then
    systemctl restart "$SERVICE_NAME.service"
fi

echo "installed: $UNIT_PATH"
if [[ "$START_SERVICE" -eq 1 ]]; then
    systemctl --no-pager --full status "$SERVICE_NAME.service" || true
else
    echo "next steps:"
    echo "  sudo systemctl enable --now $SERVICE_NAME.service"
    echo "  sudo journalctl -u $SERVICE_NAME.service -f"
fi
