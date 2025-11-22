// Drivers/bacn_api.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

#include "bacn_api.h"
#include "bacn_GPS.h"
#include "bacn_LTE.h"
#include "bacn_gpio.h"

/* Definición global de GPSInfo (antes era extern en tu código). */
GPSCommand GPSInfo;

extern bool GPS_run; /* definida en Drivers/bacn_GPS.c */
extern bool LTE_run; /* definida en Drivers/bacn_LTE.c */

/* Mutex exportado para que bacn_GPS.c pueda usarlo al actualizar GPSInfo */
pthread_mutex_t gps_mutex = PTHREAD_MUTEX_INITIALIZER;

/* Mantener estructuras UART para poder cerrarlas */
static gp_uart g_gps_uart;
static st_uart g_lte_uart;
static int g_gps_inited = 0;
static int g_lte_inited = 0;

/* Helpers para liberar campos de GPSInfo (si fueron strdup) */
static void free_gps_info_fields(void)
{
    /* GPSCommand fields son char* en tu header; liberamos si no NULL */
    if (GPSInfo.Header) { free(GPSInfo.Header); GPSInfo.Header = NULL; }
    if (GPSInfo.UTC_Time) { free(GPSInfo.UTC_Time); GPSInfo.UTC_Time = NULL; }
    if (GPSInfo.Latitude) { free(GPSInfo.Latitude); GPSInfo.Latitude = NULL; }
    if (GPSInfo.LatDir) { free(GPSInfo.LatDir); GPSInfo.LatDir = NULL; }
    if (GPSInfo.Longitude) { free(GPSInfo.Longitude); GPSInfo.Longitude = NULL; }
    if (GPSInfo.LonDir) { free(GPSInfo.LonDir); GPSInfo.LonDir = NULL; }
    if (GPSInfo.Quality) { free(GPSInfo.Quality); GPSInfo.Quality = NULL; }
    if (GPSInfo.Satelites) { free(GPSInfo.Satelites); GPSInfo.Satelites = NULL; }
    if (GPSInfo.HDOP) { free(GPSInfo.HDOP); GPSInfo.HDOP = NULL; }
    if (GPSInfo.Altitude) { free(GPSInfo.Altitude); GPSInfo.Altitude = NULL; }
    if (GPSInfo.Units_al) { free(GPSInfo.Units_al); GPSInfo.Units_al = NULL; }
    if (GPSInfo.Undulation) { free(GPSInfo.Undulation); GPSInfo.Undulation = NULL; }
    if (GPSInfo.Units_un) { free(GPSInfo.Units_un); GPSInfo.Units_un = NULL; }
    if (GPSInfo.Age) { free(GPSInfo.Age); GPSInfo.Age = NULL; }
    if (GPSInfo.Cheksum) { free(GPSInfo.Cheksum); GPSInfo.Cheksum = NULL; }
}

/* api_init_gps: inicia GPS (envuelve init_usart1) */
int api_init_gps(void)
{
    if (g_gps_inited) return 0; /* ya iniciado */

    memset(&g_gps_uart, 0, sizeof(g_gps_uart));
    if (init_usart1(&g_gps_uart) != 0) {
        return -1;
    }
    g_gps_inited = 1;
    return 0;
}

/* api_init_lte: inicia LTE (envuelve init_usart) */
int api_init_lte(void)
{
    if (g_lte_inited) return 0;

    memset(&g_lte_uart, 0, sizeof(g_lte_uart));
    if (init_usart(&g_lte_uart) != 0) {
        return -1;
    }
    g_lte_inited = 1;
    return 0;
}

int api_init_all(void)
{
    int r;
    r = api_init_lte();
    if (r != 0) return r;
    r = api_init_gps();
    return r;
}

/* Close / stop */
int api_close_gps(void)
{
    if (!g_gps_inited) return 0;
    GPS_run = false; /* variable en bacn_GPS.c */
    close_usart1(&g_gps_uart);
    pthread_mutex_lock(&gps_mutex);
    free_gps_info_fields();
    pthread_mutex_unlock(&gps_mutex);
    g_gps_inited = 0;
    return 0;
}

int api_close_lte(void)
{
    if (!g_lte_inited) return 0;
    LTE_run = false; /* variable en bacn_LTE.c */
    close_usart(&g_lte_uart);
    g_lte_inited = 0;
    return 0;
}

int api_close_all(void)
{
    api_close_gps();
    api_close_lte();
    return 0;
}

/* Antenna wrappers */
int api_select_antenna(int antenna)
{
    select_ANTENNA((uint8_t)antenna);
    return 0;
}

int api_switch_antenna(int ant_id, int state)
{
    switch (ant_id) {
        case 1: return switch_ANTENNA1(state ? 1 : 0);
        case 2: return switch_ANTENNA2(state ? 1 : 0);
        case 3: return switch_ANTENNA3(state ? 1 : 0);
        case 4: return switch_ANTENNA4(state ? 1 : 0);
        default: return -1;
    }
}

/* Getters seguros: copian dentro del buffer del llamador */
static int copy_field(const char *src, char *dst, size_t dst_len)
{
    if (!src || src[0] == '\0') return -1;
    if (!dst || dst_len == 0) return -1;
    strncpy(dst, src, dst_len - 1);
    dst[dst_len - 1] = '\0';
    return 0;
}

int api_get_latitude(char *buf, size_t buf_len)
{
    int r = -1;
    pthread_mutex_lock(&gps_mutex);
    r = copy_field(GPSInfo.Latitude, buf, buf_len);
    pthread_mutex_unlock(&gps_mutex);
    return r;
}

int api_get_longitude(char *buf, size_t buf_len)
{
    int r = -1;
    pthread_mutex_lock(&gps_mutex);
    r = copy_field(GPSInfo.Longitude, buf, buf_len);
    pthread_mutex_unlock(&gps_mutex);
    return r;
}

int api_get_altitude(char *buf, size_t buf_len)
{
    int r = -1;
    pthread_mutex_lock(&gps_mutex);
    r = copy_field(GPSInfo.Altitude, buf, buf_len);
    pthread_mutex_unlock(&gps_mutex);
    return r;
}
