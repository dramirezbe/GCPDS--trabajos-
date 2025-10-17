#!/usr/bin/env python3
"""@file sync_cron.py
@brief Crontab scheduler for task, uses http to GET jobs and then assign times to each job with crontab
"""
import cfg

log = cfg.get_logger()
if cfg.VERBOSE:
    log.info("Started")

import time

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
        raise ValueError("cycle_s debe ser al menos 300 segundos (5 minutos).")
    if start_ms > end_ms:
        raise ValueError("start_ms debe ser menor o igual a end_ms.")

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
