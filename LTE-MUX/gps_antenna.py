#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gps_antenna.py

Pequeño cliente Python que usa ctypes para hablar con libbacn.so.

Funciones expuestas:
- init_all(), init_gps(), init_lte()
- select_antenna(n)
- switch_antenna(n, state)
- get_latitude(), get_longitude(), get_altitude()
"""

import ctypes
from ctypes import CDLL, c_int, c_char_p, c_size_t, create_string_buffer
import os
import time

# --------------------------------------------------------------------
# Cargar biblioteca compartida
# --------------------------------------------------------------------

# Busca la lib en el directorio actual
LIB_PATH = os.path.join(os.path.dirname(__file__), "libbacn.so")
lib = CDLL(LIB_PATH)

# --------------------------------------------------------------------
# Declaración de prototipos
# --------------------------------------------------------------------

lib.api_init_all.argtypes = []
lib.api_init_all.restype = c_int

lib.api_init_gps.argtypes = []
lib.api_init_gps.restype = c_int

lib.api_init_lte.argtypes = []
lib.api_init_lte.restype = c_int

lib.api_close_all.argtypes = []
lib.api_close_all.restype = c_int

lib.api_select_antenna.argtypes = [c_int]
lib.api_select_antenna.restype = c_int

lib.api_switch_antenna.argtypes = [c_int, c_int]
lib.api_switch_antenna.restype = c_int

lib.api_get_latitude.argtypes = [c_char_p, c_size_t]
lib.api_get_latitude.restype = c_int

lib.api_get_longitude.argtypes = [c_char_p, c_size_t]
lib.api_get_longitude.restype = c_int

lib.api_get_altitude.argtypes = [c_char_p, c_size_t]
lib.api_get_altitude.restype = c_int


# --------------------------------------------------------------------
# Helpers Python
# --------------------------------------------------------------------

def get_string(getter_fn):
    buf = create_string_buffer(128)
    rc = getter_fn(buf, len(buf))
    if rc == 0:
        return buf.value.decode(errors="ignore")
    return None


def get_latitude():
    return get_string(lib.api_get_latitude)

def get_longitude():
    return get_string(lib.api_get_longitude)

def get_altitude():
    return get_string(lib.api_get_altitude)


# --------------------------------------------------------------------
# Ejemplo de uso
# --------------------------------------------------------------------
if __name__ == "__main__":
    print("Iniciando módulos…")
    if lib.api_init_all() != 0:
        raise RuntimeError("Error en api_init_all()")

    print("Módulos inicializados")

    print("\nSeleccionando antena 1…")
    lib.api_select_antenna(1)

    print("Activando antena 3…")
    lib.api_switch_antenna(3, 1)
    time.sleep(1)
    print("Desactivando antena 3…")
    lib.api_switch_antenna(3, 0)

    print("\nLeyendo GPS (espera que el thread procese NMEA)…")
    for _ in range(10):
        lat = get_latitude()
        lon = get_longitude()
        alt = get_altitude()
        print("GPS:", lat, lon, alt)
        time.sleep(1)

    print("\nCerrando…")
    lib.api_close_all()
