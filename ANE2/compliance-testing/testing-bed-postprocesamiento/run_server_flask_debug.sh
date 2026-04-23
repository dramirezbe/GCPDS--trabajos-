#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${ROOT_DIR:-$SCRIPT_DIR}"
POST_DIR_NAME="postprocesamiento"
HOST="127.0.0.1"
PORT="8000"
VENV_DIR_INPUT="${VENV_DIR:-}"
DRY_RUN="0"

resolve_path() {
  local candidate="$1"
  if [[ "$candidate" = /* ]]; then
    printf '%s\n' "$candidate"
  else
    printf '%s\n' "$ROOT_DIR/$candidate"
  fi
}

detect_venv_dir() {
  local candidates=(
    "$ROOT_DIR/venv"
    "$ROOT_DIR/.venv"
    "$ROOT_DIR/$POST_DIR_NAME/venv"
    "$ROOT_DIR/$POST_DIR_NAME/.venv"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate/bin/activate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

usage() {
  cat <<EOF
Uso: $(basename "$0") [-r post_dir] [-p puerto] [-h host] [-v venv_dir] [-n]

Opciones:
  -r POST_DIR  Carpeta del servidor. Puede ser relativa a $ROOT_DIR o absoluta.
  -p PUERTO    Puerto para server_flask.py (default: 8000)
  -h HOST      Host para server_flask.py (default: 127.0.0.1)
  -v VENV_DIR  Carpeta del entorno virtual. Puede ser relativa a $ROOT_DIR o absoluta.
  -n           Muestra las rutas resueltas y termina sin arrancar el servidor.
EOF
}

while getopts ":r:p:h:v:n" opt; do
  case "$opt" in
    r)
      POST_DIR_NAME="$OPTARG"
      ;;
    p)
      PORT="$OPTARG"
      ;;
    h)
      HOST="$OPTARG"
      ;;
    v)
      VENV_DIR_INPUT="$OPTARG"
      ;;
    n)
      DRY_RUN="1"
      ;;
    :)
      echo "Falta valor para -$OPTARG" >&2
      usage >&2
      exit 1
      ;;
    \?)
      echo "Opción inválida: -$OPTARG" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -n "$VENV_DIR_INPUT" ]]; then
  VENV_DIR="$(resolve_path "$VENV_DIR_INPUT")"
else
  if ! VENV_DIR="$(detect_venv_dir)"; then
    echo "No encontré un venv en $ROOT_DIR ni dentro de $ROOT_DIR/$POST_DIR_NAME" >&2
    echo "Prueba con -v RUTA_DEL_VENV o define la variable VENV_DIR." >&2
    exit 1
  fi
fi

POST_DIR="$(resolve_path "$POST_DIR_NAME")"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "No existe el venv en $VENV_DIR" >&2
  exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "No encontré $VENV_DIR/bin/activate" >&2
  exit 1
fi

if [[ ! -d "$POST_DIR" ]]; then
  echo "No existe el directorio $POST_DIR" >&2
  exit 1
fi

ANE_LIC_CSV_DEFAULT="$POST_DIR/consolidado_bbdd_asignación.csv"
if [[ ! -f "$ANE_LIC_CSV_DEFAULT" ]]; then
  echo "No encontré el CSV de licencias en $ANE_LIC_CSV_DEFAULT" >&2
  exit 1
fi

echo "ROOT_DIR=$ROOT_DIR"
echo "POST_DIR=$POST_DIR"
echo "VENV_DIR=$VENV_DIR"
echo "ANE_LIC_CSV=$ANE_LIC_CSV_DEFAULT"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run solicitado. No se iniciará el servidor."
  exit 0
fi

source "$VENV_DIR/bin/activate"

cd "$POST_DIR"

export ANE_LIC_CSV="$ANE_LIC_CSV_DEFAULT"
unset ANE_ALLOW_JSON_PATH

echo "Usando venv: $VENV_DIR"
echo "ANE_LIC_CSV=$ANE_LIC_CSV"
echo "Iniciando server_flask.py en $HOST:$PORT"

exec python server_flask.py --host "$HOST" --port "$PORT" --debug
