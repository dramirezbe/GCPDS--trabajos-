#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: createAdminDevlopment.sh -r path_dotenv

Creates admin user if it does not exist, using DB credentials from the provided .env file.
Creates:
  username: admin
  password: admin123 (stored as bcrypt hash)
  role: administrador
  is_active: true
EOF
}

dotenv_path=""

while getopts ":r:h" opt; do
  case "$opt" in
    r)
      dotenv_path="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    :)
      echo "Error: option -$OPTARG requires an argument." >&2
      usage
      exit 1
      ;;
    \?)
      echo "Error: invalid option -$OPTARG" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$dotenv_path" ]]; then
  echo "Error: missing required -r path_dotenv" >&2
  usage
  exit 1
fi

if [[ ! -f "$dotenv_path" ]]; then
  echo "Error: .env file not found at: $dotenv_path" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Error: node is required but was not found in PATH." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql is required but was not found in PATH." >&2
  exit 1
fi

# Export all vars from provided dotenv file
set -a
# shellcheck disable=SC1090
source "$dotenv_path"
set +a

required_vars=(DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD)
for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Error: missing required variable in .env: $v" >&2
    exit 1
  fi
done

# Create bcrypt hash for admin123 using local node runtime
admin_hash="$(node -e "const bcrypt=require('bcrypt'); bcrypt.hash('admin123',10).then(h=>process.stdout.write(h)).catch(()=>process.exit(1));")"

if [[ -z "$admin_hash" ]]; then
  echo "Error: could not generate bcrypt hash." >&2
  exit 1
fi

export PGPASSWORD="$DB_PASSWORD"

user_exists="$(psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -tAc "SELECT EXISTS(SELECT 1 FROM users WHERE username='admin');")"

if [[ "$user_exists" == "t" ]]; then
  echo "admin already exists. No changes made."
  exit 0
fi

psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -v ON_ERROR_STOP=1 \
  -c "INSERT INTO users (username, password, full_name, email, role, is_active) VALUES ('admin', '$admin_hash', 'Administrador', 'admin@ane.gov.co', 'administrador', true);"

echo "admin user created successfully (username: admin, password: admin123)."