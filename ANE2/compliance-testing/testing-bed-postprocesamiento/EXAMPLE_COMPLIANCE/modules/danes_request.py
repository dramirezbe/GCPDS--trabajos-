from __future__ import annotations

import os
import select
import socketserver
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

import paramiko
import requests
from flask import Flask, jsonify, request

DEFAULT_TIMEOUT = 20.0

#Copypaste here credentials DANES

#Copypaste here credentials DANES

@dataclass(slots=True)
class DaneTunnelConfig:
    ssh_host: str
    ssh_port: int
    ssh_user: str
    ssh_pass: str
    remote_service_host: str
    remote_service_port: int
    local_bind_host: str = "127.0.0.1"

    @classmethod
    def from_env(cls) -> "DaneTunnelConfig":
        return cls(
            ssh_host=os.environ.get("DANE_TUNNEL_SSH_HOST", "heremyssh.dane.gov.co"),
            ssh_port=int(os.environ.get("DANE_TUNNEL_SSH_PORT", "22")),
            ssh_user=os.environ.get("DANE_TUNNEL_SSH_USER", "user"),
            ssh_pass=os.environ.get("DANE_TUNNEL_SSH_PASS", 'password_ssh_tunnel'),
            remote_service_host=os.environ.get("DANE_TUNNEL_REMOTE_HOST", "my_ip.hostedservice.com"),
            remote_service_port=int(os.environ.get("DANE_TUNNEL_REMOTE_PORT", "12345")),
            local_bind_host=os.environ.get("DANE_TUNNEL_LOCAL_BIND_HOST", "127.0.0.1"),
        )


class _ForwardServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _ForwardHandler(socketserver.BaseRequestHandler):
    ssh_transport: paramiko.Transport | None = None
    remote_host: str = "127.0.0.1"
    remote_port: int = 0

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


def _create_ssh_client(config: DaneTunnelConfig) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config.ssh_host,
        port=config.ssh_port,
        username=config.ssh_user,
        password=config.ssh_pass,
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
    config: DaneTunnelConfig,
    local_port: int = 0,
) -> tuple[_ForwardServer, threading.Thread]:
    handler = type(
        "ForwardHandler",
        (_ForwardHandler,),
        {
            "ssh_transport": ssh_transport,
            "remote_host": config.remote_service_host,
            "remote_port": config.remote_service_port,
        },
    )

    server = _ForwardServer((config.local_bind_host, local_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def query_location(base_url: str, *, lat: float, lon: float, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
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


def collect_dane_codes(data: Dict[str, Any]) -> List[str]:
    result = data.get("resultado") or {}
    codes: List[str] = []

    central = result.get("central") or {}
    central_code = central.get("codigo_dane")
    if central_code:
        codes.append(str(central_code).strip())

    for row in result.get("adyacentes") or []:
        code = row.get("codigo_dane")
        if not code:
            continue
        normalized = str(code).strip()
        if normalized not in codes:
            codes.append(normalized)

    return codes


@contextmanager
def open_tunnel(
    config: DaneTunnelConfig | None = None,
    *,
    local_port: int = 0,
) -> Iterator[str]:
    active_config = config or DaneTunnelConfig.from_env()
    ssh_client = _create_ssh_client(active_config)
    server = None

    try:
        transport = ssh_client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError("La conexión SSH no quedó activa.")

        server, _thread = _start_tunnel(
            transport,
            config=active_config,
            local_port=local_port,
        )
        bound_port = server.server_address[1]
        yield f"http://{active_config.local_bind_host}:{bound_port}"
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        ssh_client.close()


def query_location_via_tunnel(
    lat: float,
    lon: float,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    config: DaneTunnelConfig | None = None,
) -> Dict[str, Any]:
    with open_tunnel(config=config) as base_url:
        return query_location(base_url, lat=lat, lon=lon, timeout=timeout)


def get_dane_codes_via_tunnel(
    lat: float,
    lon: float,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    config: DaneTunnelConfig | None = None,
) -> List[str]:
    data = query_location_via_tunnel(lat, lon, timeout=timeout, config=config)
    return collect_dane_codes(data)


class DaneTunnelClient:
    def __init__(
        self,
        config: DaneTunnelConfig | None = None,
        *,
        default_timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.config = config or DaneTunnelConfig.from_env()
        self.default_timeout = default_timeout

    def query_location(self, lat: float, lon: float, *, timeout: float | None = None) -> Dict[str, Any]:
        return query_location_via_tunnel(
            lat,
            lon,
            timeout=self.default_timeout if timeout is None else timeout,
            config=self.config,
        )

    def get_dane_codes(self, lat: float, lon: float, *, timeout: float | None = None) -> List[str]:
        data = self.query_location(lat, lon, timeout=timeout)
        return collect_dane_codes(data)


def create_mock_app(client: DaneTunnelClient | None = None) -> Flask:
    app = Flask(__name__)
    dane_client = client or DaneTunnelClient()

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

        timeout = float(request.args.get("timeout", os.environ.get("DANE_TUNNEL_TIMEOUT", str(DEFAULT_TIMEOUT))))

        try:
            data = dane_client.query_location(lat, lon, timeout=timeout)
            return jsonify(data)
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else 502
            return jsonify(
                {
                    "error": "Error del servicio de geolocalización remoto",
                    "details": response.text if response is not None else str(exc),
                }
            ), status_code
        except Exception as exc:
            return jsonify(
                {
                    "error": "No fue posible consultar la geolocalización por túnel",
                    "details": str(exc),
                }
            ), 502

    return app


def full_example_dane_tunnel(lat: float, lon: float, timeout: float = DEFAULT_TIMEOUT) -> List[str] | None:
    dane_codes = get_dane_codes_via_tunnel(lat, lon, timeout=timeout)
    return dane_codes if dane_codes else None


__all__ = [
    "DEFAULT_TIMEOUT",
    "DaneTunnelClient",
    "DaneTunnelConfig",
    "collect_dane_codes",
    "create_mock_app",
    "full_example_dane_tunnel",
    "get_dane_codes_via_tunnel",
    "open_tunnel",
    "query_location",
    "query_location_via_tunnel",
]
