#!/usr/bin/env python3
"""Generate an interactive HTML map with client-side DANE filters."""

from __future__ import annotations

import argparse
import csv
import functools
import http.server
import json
import math
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any


EARTH_RADIUS_KM = 6371.0088
DEFAULT_LAT = 4.6775
DEFAULT_LON = -74.0541
DEFAULT_FREQ_INF_MHZ = 484.9
DEFAULT_FREQ_SUP_MHZ = 485.1
DEFAULT_RADIUS_KM = 30.0
DEFAULT_MAX_RENDERED = 3000
DEFAULT_CSV = (
    Path(__file__).resolve().parent
    / "new-postprocesamiento"
    / "consolidado_bbdd_asignaci\u00f3n.csv"
)
DEFAULT_OUTPUT = Path("int_map_danes.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genera un mapa HTML interactivo con controles en la pagina para "
            "latitud, longitud, rango de frecuencia y radio. "
            "Si no pasas parametros, usa: "
            f"{DEFAULT_LAT} {DEFAULT_LON} {DEFAULT_FREQ_INF_MHZ} "
            f"{DEFAULT_FREQ_SUP_MHZ} {DEFAULT_RADIUS_KM}"
        )
    )
    parser.add_argument(
        "lat",
        nargs="?",
        type=float,
        default=DEFAULT_LAT,
        help=f"Latitud central en grados decimales. Por defecto: {DEFAULT_LAT}",
    )
    parser.add_argument(
        "lon",
        nargs="?",
        type=float,
        default=DEFAULT_LON,
        help=f"Longitud central en grados decimales. Por defecto: {DEFAULT_LON}",
    )
    parser.add_argument(
        "freq_inf_mhz",
        nargs="?",
        type=float,
        default=DEFAULT_FREQ_INF_MHZ,
        help=(
            "Frecuencia inferior en MHz. "
            f"Por defecto: {DEFAULT_FREQ_INF_MHZ}"
        ),
    )
    parser.add_argument(
        "freq_sup_mhz",
        nargs="?",
        type=float,
        default=DEFAULT_FREQ_SUP_MHZ,
        help=(
            "Frecuencia superior en MHz. "
            f"Por defecto: {DEFAULT_FREQ_SUP_MHZ}"
        ),
    )
    parser.add_argument(
        "km",
        nargs="?",
        type=float,
        default=DEFAULT_RADIUS_KM,
        help=f"Radio de busqueda en kilometros. Por defecto: {DEFAULT_RADIUS_KM}",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        type=Path,
        help=f"Ruta del CSV de licencias. Por defecto: {DEFAULT_CSV}",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        type=Path,
        help=f"HTML de salida. Por defecto: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--max-rendered",
        type=int,
        default=DEFAULT_MAX_RENDERED,
        help=(
            "Maximo de puntos que se dibujan a la vez para no sobrecargar el navegador. "
            f"Por defecto: {DEFAULT_MAX_RENDERED}"
        ),
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Genera el HTML sin intentar abrirlo en el navegador.",
    )
    parser.add_argument(
        "--open-mode",
        choices=("server", "file"),
        default="server",
        help=(
            "Como abrir el mapa si no usas --no-open. "
            "'server' evita bloqueos de tiles al servir el HTML por localhost."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host para servir el HTML cuando --open-mode server. Por defecto: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help=(
            "Puerto para servir el HTML cuando --open-mode server. "
            "Usa 0 para elegir uno libre automaticamente."
        ),
    )
    return parser.parse_args()


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_dataset(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")

    points: list[dict[str, Any]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "codigo_dane",
            "frecuencia",
            "latitud_dec",
            "longitud_dec",
            "distintivo",
            "estado",
            "servicio",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "Al CSV le faltan columnas requeridas: " + ", ".join(sorted(missing))
            )

        for row in reader:
            frequency = to_float(row.get("frecuencia"))
            lat = to_float(row.get("latitud_dec"))
            lon = to_float(row.get("longitud_dec"))
            if frequency is None or lat is None or lon is None:
                continue

            points.append(
                {
                    "codigo_dane": str(row.get("codigo_dane", "")).strip(),
                    "frecuencia": frequency,
                    "lat": lat,
                    "lon": lon,
                    "distintivo": str(row.get("distintivo", "")).strip(),
                    "estado": str(row.get("estado", "")).strip(),
                    "servicio": str(row.get("servicio", "")).strip(),
                }
            )

    points.sort(key=lambda item: (item["frecuencia"], item["codigo_dane"]))
    return points


def filter_points(
    points: list[dict[str, Any]],
    center_lat: float,
    center_lon: float,
    freq_inf_mhz: float,
    freq_sup_mhz: float,
    radius_km: float,
) -> list[dict[str, Any]]:
    lower = min(freq_inf_mhz, freq_sup_mhz)
    upper = max(freq_inf_mhz, freq_sup_mhz)
    filtered: list[dict[str, Any]] = []

    for point in points:
        frequency = point["frecuencia"]
        if not lower <= frequency <= upper:
            continue

        distance = haversine_km(center_lat, center_lon, point["lat"], point["lon"])
        if distance > radius_km:
            continue

        filtered.append(
            {
                **point,
                "distancia_km": round(distance, 3),
            }
        )

    filtered.sort(key=lambda item: (item["distancia_km"], item["frecuencia"]))
    return filtered


def js_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def build_html(
    all_points: list[dict[str, Any]],
    initial_state: dict[str, float],
    max_rendered: int,
) -> str:
    template = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mapa interactivo DANE</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    :root {
      color-scheme: light;
      --panel-border: #d9e1ea;
      --panel-bg: #f8fafc;
      --text-main: #122033;
      --text-soft: #51606f;
      --accent: #0f62fe;
      --accent-dark: #0a4fd6;
      --danger: #b42318;
    }
    html, body {
      height: 100%;
      margin: 0;
      font-family: Arial, sans-serif;
      color: var(--text-main);
      background: #edf2f7;
    }
    body {
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .toolbar {
      display: grid;
      gap: 12px;
      padding: 12px 14px;
      background: #ffffff;
      border-bottom: 1px solid var(--panel-border);
    }
    .toolbar-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }
    .title {
      display: grid;
      gap: 2px;
    }
    .title h1 {
      margin: 0;
      font-size: 18px;
    }
    .title p {
      margin: 0;
      color: var(--text-soft);
      font-size: 13px;
    }
    .controls-form {
      display: grid;
      gap: 12px;
    }
    .controls-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      align-items: end;
    }
    .field {
      display: grid;
      gap: 5px;
    }
    .field label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-soft);
    }
    .field input {
      height: 38px;
      padding: 0 10px;
      border: 1px solid #c8d2dc;
      border-radius: 6px;
      font-size: 14px;
      color: var(--text-main);
      background: #ffffff;
    }
    .field input:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15, 98, 254, 0.12);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      height: 38px;
      padding: 0 14px;
      border: 1px solid transparent;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }
    .btn-primary {
      background: var(--accent);
      color: white;
    }
    .btn-primary:hover {
      background: var(--accent-dark);
    }
    .btn-secondary {
      background: white;
      color: var(--text-main);
      border-color: #c8d2dc;
    }
    .btn-secondary:hover {
      background: #f3f6f9;
    }
    .status-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .summary {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .summary-chip {
      padding: 6px 10px;
      border: 1px solid var(--panel-border);
      border-radius: 999px;
      background: var(--panel-bg);
      font-size: 12px;
      white-space: nowrap;
    }
    .status {
      font-size: 13px;
      color: var(--text-soft);
    }
    .status.error {
      color: var(--danger);
      font-weight: 600;
    }
    .command-box {
      display: grid;
      gap: 6px;
    }
    .command-box label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-soft);
    }
    .command-output {
      min-height: 38px;
      padding: 9px 10px;
      border: 1px solid var(--panel-border);
      border-radius: 6px;
      background: var(--panel-bg);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    #map {
      width: 100%;
      height: 100%;
      background: #dbe4ee;
    }
    .leaflet-tooltip {
      font-size: 12px;
      font-weight: 600;
    }
    .popup-table {
      border-collapse: collapse;
      font-size: 13px;
      min-width: 240px;
    }
    .popup-table th {
      padding: 3px 8px 3px 0;
      text-align: left;
      vertical-align: top;
      color: var(--text-soft);
      white-space: nowrap;
    }
    .popup-table td {
      padding: 3px 0;
      vertical-align: top;
      color: var(--text-main);
    }
    @media (max-width: 1100px) {
      .controls-grid {
        grid-template-columns: repeat(3, minmax(120px, 1fr));
      }
    }
    @media (max-width: 760px) {
      body {
        grid-template-rows: auto minmax(420px, 1fr);
      }
      .controls-grid {
        grid-template-columns: repeat(2, minmax(120px, 1fr));
      }
      .actions {
        width: 100%;
      }
      .actions button {
        flex: 1 1 160px;
      }
    }
    @media (max-width: 520px) {
      .controls-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <section class="toolbar">
    <div class="toolbar-top">
      <div class="title">
        <h1>Mapa interactivo DANE</h1>
        <p>Cambia latitud, longitud, frecuencia y radio desde esta misma pagina.</p>
      </div>
      <div class="actions">
        <button id="applyBtn" class="btn-primary" type="submit" form="controlsForm">Aplicar filtros</button>
        <button id="resetBtn" class="btn-secondary" type="button">Valores iniciales</button>
        <button id="copyBtn" class="btn-secondary" type="button">Copiar comando</button>
      </div>
    </div>

    <form id="controlsForm" class="controls-form">
      <div class="controls-grid">
        <div class="field">
          <label for="latInput">Latitud</label>
          <input id="latInput" name="lat" type="number" step="any">
        </div>
        <div class="field">
          <label for="lonInput">Longitud</label>
          <input id="lonInput" name="lon" type="number" step="any">
        </div>
        <div class="field">
          <label for="freqInfInput">Frecuencia inferior (MHz)</label>
          <input id="freqInfInput" name="freqInf" type="number" step="any">
        </div>
        <div class="field">
          <label for="freqSupInput">Frecuencia superior (MHz)</label>
          <input id="freqSupInput" name="freqSup" type="number" step="any">
        </div>
        <div class="field">
          <label for="kmInput">Radio (km)</label>
          <input id="kmInput" name="km" type="number" step="any" min="0">
        </div>
      </div>
    </form>

    <div class="status-row">
      <div class="summary" id="summaryChips"></div>
      <div id="statusText" class="status">Listo.</div>
    </div>

    <div class="command-box">
      <label for="commandOutput">Comando actual</label>
      <div id="commandOutput" class="command-output"></div>
    </div>
  </section>

  <div id="map"></div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const allPoints = __POINTS_JSON__;
    const defaultState = __DEFAULT_STATE_JSON__;
    const maxRenderedPoints = __MAX_RENDERED__;

    const latInput = document.getElementById("latInput");
    const lonInput = document.getElementById("lonInput");
    const freqInfInput = document.getElementById("freqInfInput");
    const freqSupInput = document.getElementById("freqSupInput");
    const kmInput = document.getElementById("kmInput");
    const summaryChips = document.getElementById("summaryChips");
    const statusText = document.getElementById("statusText");
    const commandOutput = document.getElementById("commandOutput");
    const controlsForm = document.getElementById("controlsForm");
    const resetBtn = document.getElementById("resetBtn");
    const copyBtn = document.getElementById("copyBtn");

    const map = L.map("map", { preferCanvas: true }).setView(
      [defaultState.lat, defaultState.lon],
      11
    );
    const canvasRenderer = L.canvas({ padding: 0.35 });
    const resultLayer = L.layerGroup().addTo(map);
    let lastState = { ...defaultState };

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    function haversineKm(lat1, lon1, lat2, lon2) {
      const toRad = (value) => (value * Math.PI) / 180;
      const phi1 = toRad(lat1);
      const phi2 = toRad(lat2);
      const deltaPhi = toRad(lat2 - lat1);
      const deltaLambda = toRad(lon2 - lon1);
      const a =
        Math.sin(deltaPhi / 2) ** 2 +
        Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2;
      return 6371.0088 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function formatValue(value, decimals = 4) {
      return Number(value).toFixed(decimals).replace(/\.?0+$/, "");
    }

    function formatCommandValue(value) {
      return Number(value).toFixed(6).replace(/\.?0+$/, "");
    }

    function zoomForRadius(radiusKm) {
      if (radiusKm <= 2) return 14;
      if (radiusKm <= 5) return 13;
      if (radiusKm <= 10) return 12;
      if (radiusKm <= 20) return 11;
      if (radiusKm <= 50) return 10;
      if (radiusKm <= 100) return 9;
      if (radiusKm <= 200) return 8;
      return 7;
    }

    function freqColor(freq, lower, upper) {
      if (lower === upper) {
        return "#b42318";
      }
      const t = Math.max(0, Math.min(1, (freq - lower) / (upper - lower)));
      const hue = 215 - t * 175;
      return `hsl(${hue}, 78%, 43%)`;
    }

    function popupContent(point) {
      return `
        <table class="popup-table">
          <tr><th>Codigo DANE</th><td>${escapeHtml(point.codigo_dane)}</td></tr>
          <tr><th>Frecuencia</th><td>${point.frecuencia.toFixed(3)} MHz</td></tr>
          <tr><th>Distancia</th><td>${point.distancia_km.toFixed(3)} km</td></tr>
          <tr><th>Lat / Lon</th><td>${point.lat.toFixed(6)}, ${point.lon.toFixed(6)}</td></tr>
          <tr><th>Distintivo</th><td>${escapeHtml(point.distintivo)}</td></tr>
          <tr><th>Estado</th><td>${escapeHtml(point.estado)}</td></tr>
          <tr><th>Servicio</th><td>${escapeHtml(point.servicio)}</td></tr>
        </table>
      `;
    }

    function setStatus(message, isError = false) {
      statusText.textContent = message;
      statusText.classList.toggle("error", Boolean(isError));
    }

    function setInputs(state) {
      latInput.value = formatValue(state.lat, 6);
      lonInput.value = formatValue(state.lon, 6);
      freqInfInput.value = formatValue(state.freqInf, 6);
      freqSupInput.value = formatValue(state.freqSup, 6);
      kmInput.value = formatValue(state.km, 3);
    }

    function readNumber(input, label) {
      const value = Number(input.value);
      if (!Number.isFinite(value)) {
        throw new Error(`Valor invalido para ${label}.`);
      }
      return value;
    }

    function readStateFromInputs() {
      const lat = readNumber(latInput, "latitud");
      const lon = readNumber(lonInput, "longitud");
      const freqInf = readNumber(freqInfInput, "frecuencia inferior");
      const freqSup = readNumber(freqSupInput, "frecuencia superior");
      const km = readNumber(kmInput, "radio");

      if (km < 0) {
        throw new Error("El radio en km debe ser mayor o igual a 0.");
      }

      return {
        lat,
        lon,
        freqInf: Math.min(freqInf, freqSup),
        freqSup: Math.max(freqInf, freqSup),
        km
      };
    }

    function commandForState(state) {
      return `python3 int_map_danes.py ${formatCommandValue(state.lat)} ${formatCommandValue(state.lon)} ${formatCommandValue(state.freqInf)} ${formatCommandValue(state.freqSup)} ${formatCommandValue(state.km)}`;
    }

    function updateSummary(state, totalFound, renderedCount) {
      const hidden = totalFound - renderedCount;
      const items = [
        `Total cargados: ${allPoints.length.toLocaleString("es-CO")}`,
        `Coincidencias: ${totalFound.toLocaleString("es-CO")}`,
        `En mapa: ${renderedCount.toLocaleString("es-CO")}`,
        `Frecuencia: ${formatValue(state.freqInf, 3)} - ${formatValue(state.freqSup, 3)} MHz`,
        `Centro: ${formatValue(state.lat, 5)}, ${formatValue(state.lon, 5)}`,
        `Radio: ${formatValue(state.km, 2)} km`
      ];
      if (hidden > 0) {
        items.push(`No dibujados: ${hidden.toLocaleString("es-CO")} (limite ${maxRenderedPoints.toLocaleString("es-CO")})`);
      }

      summaryChips.innerHTML = items
        .map((text) => `<span class="summary-chip">${escapeHtml(text)}</span>`)
        .join("");
    }

    function computeResults(state) {
      const results = [];
      for (const point of allPoints) {
        if (point.frecuencia < state.freqInf || point.frecuencia > state.freqSup) {
          continue;
        }
        const distance = haversineKm(state.lat, state.lon, point.lat, point.lon);
        if (distance > state.km) {
          continue;
        }
        results.push({
          ...point,
          distancia_km: distance
        });
      }

      results.sort((a, b) => {
        if (a.distancia_km !== b.distancia_km) {
          return a.distancia_km - b.distancia_km;
        }
        return a.frecuencia - b.frecuencia;
      });
      return results;
    }

    function renderState(state, fitBounds = true) {
      setInputs(state);
      commandOutput.textContent = commandForState(state);
      resultLayer.clearLayers();

      const results = computeResults(state);
      lastState = { ...state };
      const center = [state.lat, state.lon];
      const bounds = L.latLngBounds([center]);

      L.marker(center, {
        title: "Centro de busqueda"
      })
        .addTo(resultLayer)
        .bindPopup(
          `<strong>Centro de busqueda</strong><br>Lat: ${state.lat.toFixed(6)}<br>Lon: ${state.lon.toFixed(6)}`
        );

      L.circle(center, {
        radius: state.km * 1000,
        color: "#0f62fe",
        fillColor: "#78a9ff",
        fillOpacity: 0.08,
        weight: 2
      }).addTo(resultLayer);

      const visible = results.slice(0, maxRenderedPoints);
      for (const point of visible) {
        const latLng = [point.lat, point.lon];
        bounds.extend(latLng);
        L.circleMarker(latLng, {
          renderer: canvasRenderer,
          radius: 6,
          color: "#122033",
          weight: 1,
          fillColor: freqColor(point.frecuencia, state.freqInf, state.freqSup),
          fillOpacity: 0.88
        })
          .addTo(resultLayer)
          .bindTooltip(
            `DANE ${escapeHtml(point.codigo_dane)}<br>${point.frecuencia.toFixed(3)} MHz`,
            {
              direction: "top",
              sticky: true
            }
          )
          .bindPopup(popupContent(point), {
            maxWidth: 380
          });
      }

      if (fitBounds) {
        if (visible.length > 0) {
          map.fitBounds(bounds.pad(0.16));
        } else {
          map.setView(center, zoomForRadius(state.km));
        }
      }

      updateSummary(state, results.length, visible.length);

      if (results.length === 0) {
        setStatus("Sin coincidencias para esos filtros.", true);
      } else if (results.length > visible.length) {
        setStatus(
          `Se encontraron ${results.length.toLocaleString("es-CO")} puntos; se dibujan los ${visible.length.toLocaleString("es-CO")} mas cercanos.`
        );
      } else {
        setStatus(
          `Mostrando ${visible.length.toLocaleString("es-CO")} punto(s) filtrado(s).`
        );
      }
    }

    controlsForm.addEventListener("submit", (event) => {
      event.preventDefault();
      try {
        renderState(readStateFromInputs(), true);
      } catch (error) {
        setStatus(error.message || "No fue posible aplicar los filtros.", true);
      }
    });

    resetBtn.addEventListener("click", () => {
      renderState({ ...defaultState }, true);
    });

    copyBtn.addEventListener("click", async () => {
      const command = commandForState(lastState);
      try {
        await navigator.clipboard.writeText(command);
        setStatus("Comando copiado al portapapeles.");
      } catch (error) {
        setStatus("No se pudo copiar automaticamente; copia el comando manualmente.", true);
      }
    });

    setInputs(defaultState);
    renderState({ ...defaultState }, true);
  </script>
</body>
</html>
"""

    return (
        template.replace("__POINTS_JSON__", js_json(all_points))
        .replace("__DEFAULT_STATE_JSON__", js_json(initial_state))
        .replace("__MAX_RENDERED__", str(max_rendered))
    )


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def serve_and_open(output: Path, host: str, port: int) -> None:
    handler = functools.partial(QuietHTTPRequestHandler, directory=str(output.parent))
    quoted_name = urllib.parse.quote(output.name)

    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        url = f"http://{host}:{httpd.server_port}/{quoted_name}"
        print(f"Abriendo mapa por servidor local: {url}")
        print("Deja este proceso corriendo mientras uses el mapa. Ctrl+C para cerrarlo.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor local detenido.")


def main() -> int:
    args = parse_args()

    if args.km < 0:
        print("El radio en km debe ser mayor o igual a 0.", file=sys.stderr)
        return 2

    if args.max_rendered < 1:
        print("--max-rendered debe ser mayor o igual a 1.", file=sys.stderr)
        return 2

    all_points = load_dataset(args.csv)
    initial_state = {
        "lat": args.lat,
        "lon": args.lon,
        "freqInf": min(args.freq_inf_mhz, args.freq_sup_mhz),
        "freqSup": max(args.freq_inf_mhz, args.freq_sup_mhz),
        "km": args.km,
    }
    initial_results = filter_points(
        points=all_points,
        center_lat=initial_state["lat"],
        center_lon=initial_state["lon"],
        freq_inf_mhz=initial_state["freqInf"],
        freq_sup_mhz=initial_state["freqSup"],
        radius_km=initial_state["km"],
    )
    html = build_html(
        all_points=all_points,
        initial_state=initial_state,
        max_rendered=args.max_rendered,
    )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    print(f"Mapa generado: {output}")
    print(f"Licencias cargadas: {len(all_points)}")
    print(f"Puntos con filtros iniciales: {len(initial_results)}")

    if not args.no_open:
        if args.open_mode == "server":
            try:
                serve_and_open(output, args.host, args.port)
            except OSError as exc:
                print(
                    "No fue posible levantar el servidor local "
                    f"({exc}). Se abrira el HTML como archivo local.",
                    file=sys.stderr,
                )
                webbrowser.open(output.as_uri())
                print(
                    "Si el proveedor de tiles bloquea el mapa en file://, "
                    "vuelve a ejecutar el script en un entorno que permita localhost."
                )
        else:
            webbrowser.open(output.as_uri())
            print(
                "Abierto como archivo local. Si ves tiles bloqueados, usa "
                "--open-mode server o no abras el HTML con file://."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
