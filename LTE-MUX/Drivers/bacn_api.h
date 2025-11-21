// Drivers/bacn_api.h
#ifndef BACN_API_H
#define BACN_API_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>

/* Inicialización */
int api_init_gps(void);        /* inicia el hilo de GPS (init_usart1) */
int api_init_lte(void);        /* inicia el hilo de LTE (init_usart) */
int api_init_all(void);        /* inicia ambos */

/* Cierre */
int api_close_gps(void);
int api_close_lte(void);
int api_close_all(void);

/* Antena */
int api_select_antenna(int antenna);        /* 1..4 */
int api_switch_antenna(int ant_id, int state); /* ant_id 1..4, state 0/1 */

/* Getters seguros: copia en 'buf' hasta buf_len bytes (incluyendo '\0').
   Devuelven 0 en éxito, -1 si no hay dato. */
int api_get_latitude(char *buf, size_t buf_len);
int api_get_longitude(char *buf, size_t buf_len);
int api_get_altitude(char *buf, size_t buf_len);

#ifdef __cplusplus
}
#endif

#endif // BACN_API_H
