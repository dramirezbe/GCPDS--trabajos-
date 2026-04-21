from __future__ import annotations

import argparse
import json
import os
import select
import socketserver
import threading
from typing import Any, Dict, List

import paramiko
import requests
from flask import Flask, jsonify, request

#----Here hardcoded (ERASE LATER)----#
SSH_HOST = "rsm.ane.gov.co"
SSH_PORT = 1222
SSH_USER = "root"
SSH_PASS = '44"PJv43k}iS'

REMOTE_SERVICE_HOST = "172.23.80.220"
REMOTE_SERVICE_PORT = 4155
LOCAL_BIND_HOST = "127.0.0.1"
#----Here hardcoded (ERASE LATER)----#

class _ForwardServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _ForwardHandler(socketserver.BaseRequestHandler):
    ssh_transport: paramiko.Transport | None = None
    remote_host: str = REMOTE_SERVICE_HOST
    remote_port: int = REMOTE_SERVICE_PORT

    def handle(self) -> None:
        transport = self.ssh_transport
        if transport is None:
            raise RuntimeError("SSH transport no disponible para el túnel.")

        channel = transport.open_channel(
            kind="direct-tcpip",
            dest_addr=(self.remote_host, self.remote_port),
            src_addr=self.request.getpeername(),
        )

        if channel is None:
            raise RuntimeError("No se pudo abrir el canal SSH hacia el servicio remoto.")

        try:
            while True:
                read_ready, _, _ = select.select([self.request, channel], [], [], 1.0)
                if self.request in read_ready:
                    data = self.request.recv(65536)
                    if not data:
                        break
                    channel.sendall(data)
                if channel in read_ready:
                    data = channel.recv(65536)
                    if not data:
                        break
                    self.request.sendall(data)
        finally:
            channel.close()
            self.request.close()


def _create_ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        password=SSH_PASS,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
        banner_timeout=30,
        auth_timeout=30,
    )
    return client


def _start_tunnel(
    ssh_transport: paramiko.Transport,
    *,
    remote_host: str,
    remote_port: int,
    local_host: str = LOCAL_BIND_HOST,
    local_port: int = 0,
) -> tuple[_ForwardServer, threading.Thread]:
    handler = type(
        "ForwardHandler",
        (_ForwardHandler,),
        {
            "ssh_transport": ssh_transport,
            "remote_host": remote_host,
            "remote_port": remote_port,
        },
    )

    server = _ForwardServer((local_host, local_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _query_location(base_url: str, *, lat: float, lon: float, timeout: float) -> Dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/localizar",
        json={"lat": lat, "lon": lon},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _collect_dane_codes(data: Dict[str, Any]) -> List[str]:
    result = data.get("resultado") or {}
    codes: List[str] = []

    central = result.get("central") or {}
    central_code = central.get("codigo_dane")
    if central_code:
        codes.append(str(central_code).strip())

    for row in result.get("adyacentes") or []:
        code = row.get("codigo_dane")
        if code:
            normalized = str(code).strip()
            if normalized not in codes:
                codes.append(normalized)

    return codes


def _query_location_via_tunnel(lat: float, lon: float, timeout: float) -> Dict[str, Any]:
    ssh_client = _create_ssh_client()
    server = None
    try:
        transport = ssh_client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError("La conexión SSH no quedó activa.")

        server, _thread = _start_tunnel(
            transport,
            remote_host=REMOTE_SERVICE_HOST,
            remote_port=REMOTE_SERVICE_PORT,
        )
        local_port = server.server_address[1]
        base_url = f"http://{LOCAL_BIND_HOST}:{local_port}"
        return _query_location(base_url, lat=lat, lon=lon, timeout=timeout)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        ssh_client.close()


def create_mock_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "dane-proxy-via-tunnel"})

    @app.post("/localizar")
    def localizar():
        payload = request.get_json(force=True, silent=False) or {}

        try:
            lat = float(payload["lat"])
            lon = float(payload["lon"])
        except Exception:
            return jsonify({"error": "Body inválido. Se esperan 'lat' y 'lon' numéricos."}), 400

        timeout = float(
            request.args.get(
                "timeout",
                os.environ.get("DANE_TUNNEL_TIMEOUT", "20.0"),
            )
        )

        try:
            data = _query_location_via_tunnel(lat, lon, timeout)
            return jsonify(data)
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else 502
            return jsonify({
                "error": "Error del servicio de geolocalización remoto",
                "details": response.text if response is not None else str(exc),
            }), status_code
        except Exception as exc:
            return jsonify({
                "error": "No fue posible consultar la geolocalización por túnel",
                "details": str(exc),
            }), 502

    return app

def full_example_dane_tunnel(lat: float, lon: float) -> List[str] | None:
    data = _query_location_via_tunnel(lat, lon, timeout=20.0)
    dane_codes = _collect_dane_codes(data)
    if dane_codes:
        print()
        #print("codigos_dane=" + ",".join(dane_codes))
    return dane_codes if dane_codes else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Abre un túnel SSH a la red ANE y consulta códigos DANE desde coordenadas."
    )
    parser.add_argument("--serve", action="store_true", help="Levanta un Flask local que expone /localizar y proxyfía por túnel.")
    parser.add_argument("--host", default="127.0.0.1", help="Host de escucha del mock Flask.")
    parser.add_argument("--port", type=int, default=4155, help="Puerto de escucha del mock Flask.")
    parser.add_argument("--lat", type=float, default=None, help="Latitud decimal.")
    parser.add_argument("--lon", type=float, default=None, help="Longitud decimal.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout HTTP en segundos.")
    args = parser.parse_args()

    if args.serve:
        app = create_mock_app()
        print(f"[MOCK] Listening on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
        return 0

    if args.lat is None or args.lon is None:
        raise SystemExit("Debes pasar --lat y --lon cuando no usas --serve.")

    dane_codes = full_example_dane_tunnel(args.lat, args.lon)
    if dane_codes is not None:
        print("Códigos DANE encontrados:", dane_codes)
    else:
        print("No se encontraron códigos DANE para las coordenadas proporcionadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
