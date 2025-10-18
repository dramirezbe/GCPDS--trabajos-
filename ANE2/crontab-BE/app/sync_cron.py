#!/usr/bin/env python3
"""@file sync_cron.py
@brief Crontab scheduler for task, uses http to GET jobs and then assign times to each job with crontab
"""
import cfg

log = cfg.get_logger()
if cfg.VERBOSE:
    log.info("Started")

import time
import requests
from crontab import CronTab
import sys

from libs import acquire_signal


def is_within_activation_window(start_ms: int, end_ms: int, cycle_s: int) -> bool:
    """
    Retorna True si el momento actual (epoch ms) coincide con una activación
    programada entre start_ms y end_ms, con periodo cycle_s (segundos).

    La primera activación ocurre en start_ms.
    La última activación debe ser >= end_ms.
    El ciclo mínimo permitido es 5 minutos (300 segundos).

    Tolerancia: ±30 s para compensar desfases de ejecución.
    """
    # Validaciones básicas
    if cycle_s < 300:
        log.error("cycle_s debe ser al menos 300 segundos (5 minutos).")
    if start_ms > end_ms:
        log.error("start_ms debe ser menor o igual a end_ms.")

    # Convertir a milisegundos
    cycle_ms = cycle_s * 1000
    tol_ms = 30 * 1000  # tolerancia 30 s

    # Obtener el tiempo actual en milisegundos (equivalente a Date.now())
    now_ms = int(time.time() * 1000)

    # Antes del inicio → no activo
    if now_ms < start_ms - tol_ms:
        return False

    # Calcular cuántos ciclos caben entre start y end (último >= end)
    span_ms = end_ms - start_ms
    n_cycles_needed = max(0, -(-span_ms // cycle_ms))  # ceil division

    # Última activación válida
    last_activation_ms = start_ms + n_cycles_needed * cycle_ms

    # Si ya pasó la última activación, salir
    if now_ms > last_activation_ms + tol_ms:
        return False

    # Verificar si estamos alineados con la rejilla del ciclo
    delta_ms = now_ms - start_ms
    if delta_ms < 0:
        return False

    remainder = delta_ms % cycle_ms
    aligned = (remainder <= tol_ms) or (cycle_ms - remainder <= tol_ms)

    return aligned

if __name__ == "__main__":
    try:
        cron = CronTab(user=True)
    except Exception as e:
        log.error("Failed to load crontab: %s", e)
        sys.exit(1)

    jobs = []

    response = None
    try:
        response = requests.get(cfg.API_IP + cfg.JOBS_URL, timeout=5)
        response.raise_for_status()
        json_jobs = response.json()

        if cfg.VERBOSE:
            log.info(f"GET jobs: response[{response.status_code}] json={json_jobs}")

    except requests.exceptions.HTTPError as errh:
        # errh.response suele contener el objeto response en HTTPError
        status = getattr(errh.response, "status_code", None)
        log.error("HTTP error: %s, status code: %s", errh, status)
    except requests.exceptions.ConnectionError as errc:
        # No hay response en ConnectionError
        log.error("Error connecting to API: %s", errc)
    except requests.exceptions.Timeout as errt:
        log.error("Timeout error: %s", errt)
    except requests.exceptions.RequestException as err:
        # Catch-all para requests
        log.error("Something went wrong with requests: %s", err)
    except ValueError as v:
        # JSON decoding error
        log.error("Error parsing JSON response: %s", v)
    
    if 'json_jobs' not in locals():
        log.warning("No jobs retrieved; json_jobs is not available.")
        json_jobs = None

    if json_jobs:
        campaigns = json_jobs.get("campaigns")
        if campaigns:
            for camp in campaigns:
                id_camp = camp.get("campaign_id")
                status_camp = camp.get("status")
                acquisition_period_s = camp.get("acquisition_period_s")
                timeframe = camp.get("timeframe")
                time_start = timeframe.get("start")
                time_end = timeframe.get("end")

                if is_within_activation_window(time_start, time_end, acquisition_period_s):
                    period_m = acquisition_period_s * 1000


            
        else:
            log.warning("No campaigns programmed, skipping")
    else:
        log.error("Malformatted json jobs, skipping sync_crontab")