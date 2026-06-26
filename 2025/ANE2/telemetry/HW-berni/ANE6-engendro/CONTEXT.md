# Registro de Pruebas ANE6: Configuración de Alimentación

## Regla general de hardware

- **ENGENDRO-FINAL-ANE6.csv**: es el único archivo donde tanto el HackRF como el LTE tienen conexión externa de voltaje y corriente.
- **Resto de archivos**: únicamente el módulo LTE cuenta con conexión externa; el HackRF, cuando se usa, se alimenta de la Raspberry Pi.

## 1. Métricas de red y tráfico

Archivos: **stress-***

- Contienen datos de MB transferidos, pérdida de paquetes, latencia, etc.
- Alimentación: solo LTE externo.
- **stress-LTE-engendro.csv**: estrés exclusivo del módulo LTE (ppp0).
- **stress-COMBINED-LTE-engendro.csv**: estrés simultáneo de LTE y HackRF. Evalúa el impacto del SDR en la calidad de la conexión de datos.

## 2. Métricas de hardware RPI5

Resto de archivos: contienen datos de temperatura, uso de CPU, frecuencias y consumo de la Raspberry Pi 5.

### A. Doble conexión externa (HackRF + LTE externos)

- **ENGENDRO-FINAL-ANE6.csv**: prueba de carga máxima de software, con peticiones masivas desde el backend. Es la validación final del sistema con estabilidad eléctrica total en ambos periféricos.

### B. Conexión externa parcial (solo LTE externo)

- **PETITION-SERVER-engendro-alive.csv**: igual que la anterior, con peticiones de servidor al máximo, pero con el HackRF alimentado por la RPI5.
- **COMBINED1-engendro.csv**: prueba de estrés máximo de hardware, con LTE + HackRF al límite de sample rate y ganancias.
- **just-LTE-engendro.csv**: estrés exclusivo de LTE a través de ppp0.
- **just-HACKRF-engendro.csv**: estrés exclusivo de HackRF, con el comando hackrf_transfer al máximo.