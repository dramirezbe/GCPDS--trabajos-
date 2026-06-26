#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/home/javastral/GIT/GCPDS-trabajos/ANE2/compliance-testing"
POST_DIR_NAME="postprocesamiento"
HOST="127.0.0.1"
PORT="8000"

usage() {
  cat <<EOF
Uso: $(basename "$0") [-r post_dir_name] [-p puerto] [-h host]

Opciones:
  -r POST_DIR  Carpeta dentro de $ROOT_DIR con server_flask.py (default: $POST_DIR_NAME)
  -p PUERTO   Puerto para server_flask.py (default: 8000)
  -h HOST     Host para server_flask.py (default: 127.0.0.1)
EOF
}

while getopts ":r:p:h:" opt; do
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

VENV_DIR="$ROOT_DIR/venv"
POST_DIR="$ROOT_DIR/$POST_DIR_NAME"

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

source "$VENV_DIR/bin/activate"

cd "$POST_DIR"

export ANE_LIC_CSV="$POST_DIR/consolidado_bbdd_asignación.csv"
unset ANE_ALLOW_JSON_PATH

echo "Usando venv: $VENV_DIR"
echo "ANE_LIC_CSV=$ANE_LIC_CSV"
echo "Iniciando server_flask.py en $HOST:$PORT"

exec python server_flask.py --host "$HOST" --port "$PORT"
