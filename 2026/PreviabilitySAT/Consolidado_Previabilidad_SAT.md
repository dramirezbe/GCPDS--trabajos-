# Sistema de Previabilidad Técnica para Licencias Satelitales (SAT)
### Documento consolidado a partir de:
1. *Diagrama de flujo de análisis y simulaciones — Caso SAT* (PDF, v6)
2. *Core de simulaciones para previabilidad de sistemas inalámbricos* (PPTX, presentación ejecutiva)
3. *Sistema de previabilidad de licencias satelitales* (PPTX, presentación ejecutiva — junio 2026)

---

## 0. Resumen general

Los tres documentos describen, desde ángulos complementarios, un mismo proyecto: un **motor técnico de simulación** que evalúa, antes del trámite administrativo formal, si una estación terrena satelital es **previable** para efectos de licenciamiento en Colombia. El sistema no reemplaza el trámite regulatorio; genera un **concepto técnico preliminar y trazable** (mapas, métricas RF, matrices de cumplimiento) que puede alimentar procesos posteriores de radicación.

- El **PDF** documenta el **flujo funcional/lógico** del análisis: pasos, bases regulatorias consultadas y datos de salida, caso por caso.
- La **presentación 1** ("Core de simulaciones...") es el pitch ejecutivo con foco en **arquitectura, alcance, fases, roles y presupuesto**, incluyendo dos diagramas visuales (arquitectura del core y clasificación ANE de estaciones).
- La **presentación 2** ("Sistema de previabilidad de licencias satelitales") es una versión más reciente (fechada junio 2026) del mismo pitch ejecutivo, con cifras actualizadas en USD y COP y una estructura de fases ligeramente distinta (7 etapas en vez de 5).

El **alcance inicial** es consistente en los tres documentos: se cubren únicamente 3 de los 5 tipos de estación terrena definidos por la ANE:

| Código ANE | Nombre del caso | Ejemplo típico |
|---|---|---|
| **(i)** | Estación terrena con características técnicas particulares | Telepuertos/gateway, o estaciones con PIRE > 60 dBW |
| **(iii)** | Arreglo estructurado de antenas enlazado a constelación No-GEO | Telepuerto con múltiples antenas dentro de un radio de 250 m |
| **(vi)** | Estación de solo recepción por interés del PRST | Estaciones que usan únicamente el enlace descendente espacio–tierra |

Quedan **fuera de alcance** en esta fase:
- **(ii)** Grupo de estaciones de baja potencia (terminales fijos/móviles, VSAT, PIRE ≤ 60 dBW — "no protección, no interferencias").
- **(v)** Grupo de estaciones ESIM (Estación Terrena en Movimiento), sujetas a cumplimiento de reglamentos aeronáuticos, marítimos y terrestres.
- Todo el **trámite administrativo/jurídico**: radicación formal, workflow legal, firmas, notificaciones, pagos y decisión regulatoria definitiva.

---

## 1. Flujo general del análisis SAT (documento PDF)

El PDF describe el flujo maestro que aplica a cualquier caso SAT, antes de bifurcarse en el flujo específico de cada ítem:

```
Inicio (Solicitud SAT)
   ↓
Captura de datos
   ↓
Validar completitud ── (Res. 376/2022 · Apéndice 4)
   ↓ [Sí]
Validar atribución ── (CNABF · Reglamento de Radiocomunicaciones (RR) Art. 5)
   ↓
Consultar fuentes ── (Visor de Espectro · ICS Manager · MIFR/MIRF)
   ↓
Clasificar caso ── (i) · (iii) · (vi)
   ↓
Flujo específico (según clasificación)
   ↓
Consolidar y dictaminar
```

### 1.1 Regulaciones y fuentes transversales (aplican a todos los casos)

| Categoría | Base regulatoria / fuente | Uso principal en el análisis |
|---|---|---|
| Regulación nacional | Resolución MinTIC 376 de 2022 | Clasificación de estaciones, requisitos técnicos y condiciones de permiso. |
| Regulación nacional | CNABF vigente (ANE) | Validación de atribución, servicio y sentido del enlace. |
| Regulación internacional | UIT — Reglamento de Radiocomunicaciones (RR), Art. 5, 9, 11, 21 y 22; Apéndices 4 y 7 | Atribución, coordinación, notificación, límites PFD/EPFD y datos mínimos. |
| Fuentes ANE | Visor de Espectro; ICS Manager | Consulta de estaciones terrenas y asignaciones nacionales. |
| Fuentes UIT | MIFR/MIRF, SNS, SNL, GIMS, BR IFIC | Asignaciones/filings internacionales y redes satelitales. |
| Cartografía | Capas cartográficas y modelos de terreno | Ubicación, distancias y entorno geográfico. |
| Recomendaciones UIT-R | P.452, P.618, P.620, P.676, P.837, P.838, P.840, S.465, S.580, S.1323, S.1432, S.1503, S.1528, S.1428 | Modelos de propagación, interferencia y patrones de antena. |

---

### 1.2 Caso (i) — Estación terrena con características técnicas particulares

**Objetivo:** evaluar la viabilidad técnica de una estación individual con parámetros particulares y alto potencial de coordinación/interferencia.

**Flujo específico:**
```
Caso (i): Características particulares
   ↓
Entradas clave: ubicación, frecuencia, ancho de banda, PIRE/EIRP, patrón de antena, G/T
   ↓
Validar requisitos ── Res. 376/2022 · CNABF · RR Art. 5 · Ap. 4
   ↓
Cruce con fuentes ── Visor · ICS · MIFR/MIRF
   ↓
Coordinar ── RR Apéndice 7 · ITU-R P.620
   ↓
Interferencia y enlace ── P.452 · P.618 · S.465/S.580 · PFD · I/N · C/I · C/(N+I)
   ↓
Comparar umbrales ── RR Art. 21 · S.1323 · S.1432
   ↓
Dictamen
   ↓
Matriz de salida: estado · métricas · estaciones · mapa · condiciones
   ↓
Fin
```

**Fuentes principales:** Visor de Espectro, ICS Manager, MIFR/MIRF, cartografía, estaciones terrenas existentes.

**Regulación / recomendaciones y qué se verifica:**

| Base | ¿Qué se verifica? |
|---|---|
| Resolución 376/2022 | Tipo de estación, datos mínimos del trámite, requisitos técnicos y condiciones regulatorias del permiso. |
| CNABF vigente | Banda atribuida, servicio permitido y sentido del enlace (tierra-espacio / espacio-tierra). |
| RR Art. 5 | Atribución internacional y notas aplicables a la banda. |
| RR Art. 9, 21; Ap. 4 y 7 | Necesidad de coordinación, límites PFD y estructura mínima de datos / contorno de coordinación. |
| ITU-R P.620 / P.452 | Área de coordinación e interferencia entre estaciones sobre la superficie terrestre. |
| ITU-R P.618, S.465, S.580, S.1323, S.1432 | Presupuesto de enlace, patrones de antena y criterios de I/N, C/I, C/(N+I) y degradación admisible. |

**Simulaciones / cálculos:**
- Validación de datos de entrada
- Área/contorno de coordinación
- Interferencia hacia/desde estaciones cercanas
- Presupuesto de enlace y degradación
- Comparación contra umbrales ANE/UIT

**Matriz de datos de salida:**

| Campo | Contenido generado |
|---|---|
| ID | Caso, fecha y versión del análisis. |
| Estado | Previable / condicionada / no previable / requiere coordinación. |
| Atribución | Resultado CNABF y RR Art. 5. |
| Métricas RF | PFD, I/N, C/I, C/(N+I), margen y disponibilidad. |
| Coordinación | Contorno/área, estaciones afectadas, distancias y azimuts. |
| Mapas | Ubicación y entorno cartográfico relevante. |
| Condiciones | Restricciones técnicas y medidas sugeridas. |
| Trazabilidad | Fuentes y normas aplicadas al análisis. |

---

### 1.3 Caso (iii) — Arreglo estructurado de antenas enlazado a constelación No-GEO

**Objetivo:** evaluar la compatibilidad técnica de un conjunto de antenas enlazado a una constelación No-GEO, incluyendo geometría temporal y compatibilidad GSO/No-GSO.

**Flujo específico:**
```
Caso (iii): Arreglo No-GEO
   ↓
Entradas clave: sitio, número de antenas, filing, frecuencia, ancho de banda, EIRP
   ↓
Validar requisitos ── Res. 376/2022 · CNABF · RR Art. 5 · Ap. 4
   ↓
Cruce con fuentes ── Visor · ICS · MIFR/MIRF · SNS/SNL/GIMS
   ↓
Geometría temporal ── visibilidad, elevación/azimut, agregación
   ↓
Coordinación local ── RR Apéndice 7 · ITU-R P.620
   ↓
Compatibilidad GSO/No-GSO ── RR Art. 22 · S.1503 · EPFD/PFD
   ↓
Dictamen
   ↓
Matriz de salida: estado · EPFD/PFD · agregación · restricciones
   ↓
Fin
```

**Fuentes principales:** Visor de Espectro, ICS Manager, MIFR/MIRF, SNS/SNL/GIMS, datos orbitales, cartografía.

**Regulación / recomendaciones y qué se verifica:**

| Base | ¿Qué se verifica? |
|---|---|
| Resolución 376/2022 | Clasificación del arreglo No-GEO, condiciones del permiso y requisitos de información del sitio/antenas. |
| CNABF vigente | Disponibilidad de banda, servicio satelital aplicable y sentido del enlace. |
| RR Art. 5 | Atribución internacional y notas reglamentarias de la banda. |
| RR Art. 21, 22; Ap. 4 y 7 | Límites PFD/EPFD, datos mínimos del filing y necesidades de coordinación local. |
| ITU-R P.620 | Coordinación/coexistencia local con otras estaciones cercanas. |
| ITU-R S.1503, S.1528, S.1428, S.1323 | Metodología No-GEO, patrones satelitales y criterios de interferencia/EPFD preliminar. |

**Simulaciones / cálculos:**
- Validación de datos y filing
- Geometría temporal y visibilidad satelital
- Coordinación local
- Compatibilidad GSO/No-GSO
- EPFD preliminar y métricas agregadas

**Matriz de datos de salida:**

| Campo | Contenido generado |
|---|---|
| ID | Caso, fecha y versión del análisis. |
| Estado | Previable / condicionada / no previable / requiere coordinación. |
| Atribución | Resultado CNABF y filing/constelación asociados. |
| Geometría | Satélites visibles, elevación/azimut y ventanas temporales. |
| Métricas No-GEO | EPFD preliminar, PFD, I/N, C/I, C/(N+I) y percentiles. |
| Agregación | Resultado de múltiples antenas/haces y coexistencia local. |
| Coordinación | Estaciones afectadas y restricciones técnicas. |
| Trazabilidad | Fuentes y normas aplicadas al análisis. |

---

### 1.4 Caso (vi) — Estación de solo recepción por interés del PRST

**Objetivo:** evaluar si una estación receptora puede operar con calidad suficiente y si el entorno radioeléctrico permite protegerla o condicionarla.

**Flujo específico:**
```
Caso (vi): Solo recepción
   ↓
Entradas clave: ubicación, frecuencia de bajada, ancho de banda, G/T, sensibilidad
   ↓
Validar requisitos ── Res. 376/2022 · CNABF · RR Art. 5 · Ap. 4
   ↓
Cruce con fuentes ── Visor · ICS · MIFR/MIRF · transmisores y satélites cercanos
   ↓
Señal deseada ── P.618 · P.676 · P.837 · C/N base
   ↓
Entorno interferente ── P.452 · S.465/S.580 · I/N · C/I · C/(N+I)
   ↓
¿Protegible? (Sí/No)
   ↓
Matriz de salida: estado · calidad · interferentes · mitigación
   ↓
Fin
```

**Fuentes principales:** Visor de Espectro, ICS Manager, MIFR/MIRF, transmisores cercanos, satélites vecinos, cartografía.

**Regulación / recomendaciones y qué se verifica:**

| Base | ¿Qué se verifica? |
|---|---|
| Resolución 376/2022 | Clasificación como solo recepción, información mínima, requisitos técnicos y condiciones del permiso. |
| CNABF vigente | Validez de la banda y del enlace descendente solicitado. |
| RR Art. 5 | Atribución internacional y notas aplicables al servicio de recepción. |
| RR Art. 21; Ap. 4 y 7 | Límites relevantes de emisiones / datos mínimos y coordinación cuando aplique. |
| ITU-R P.452 | Interferencia proveniente de estaciones sobre la superficie terrestre. |
| ITU-R P.618, P.676, P.837, P.838, P.840 | Señal deseada, disponibilidad y pérdidas de propagación tierra-espacio/espacio-tierra. |
| ITU-R S.465, S.580, S.1323, S.1432 | Patrones de antena, I/N, C/I, C/(N+I), protectibilidad y degradación admisible. |

**Simulaciones / cálculos:**
- Cálculo de señal deseada
- Disponibilidad base
- Interferencia co-canal/adyacente
- Márgenes y protectibilidad
- Medidas de mitigación y coordinación

**Matriz de datos de salida:**

| Campo | Contenido generado |
|---|---|
| ID | Caso, fecha y versión del análisis. |
| Estado | Previable / condicionada / no previable / requiere coordinación. |
| Atribución | Resultado CNABF y RR Art. 5. |
| Señal deseada | C/N base, disponibilidad, G/T y sensibilidad. |
| Interferencia | I/N, C/I, C/(N+I) e interferentes relevantes. |
| Protección | Resultado de protectibilidad y viabilidad bajo condiciones. |
| Mitigación | Filtros, reubicación, restricciones o coordinación. |
| Trazabilidad | Fuentes y normas aplicadas al análisis. |

---

## 2. Presentación 1 — "Core de simulaciones para previabilidad de sistemas inalámbricos"

Presentación ejecutiva (11 láminas): fases, alcance, tiempos, equipo y costos de referencia.

### Diapositiva 1 — Portada
- **Título:** Core de simulaciones para previabilidad de sistemas inalámbricos.
- Alcance inicial SAT: ítems 1, 3 y 4. No incluye trámite administrativo. Diseñado para crecer hacia PMP (punto-multipunto) y microondas.
- Esquema resumido: **Core común** (RF · GIS · reglas · reportes) → **SAT inicial** (ítems 1, 3 y 4) → **API/Web services** (interfaz de prueba) → **PMP + MW** (futuro).
- Decisiones posibles del simulador: **previable · condicionado · no previable · requiere coordinación · información insuficiente.**

### Diapositiva 2 — Alcance exacto del primer desarrollo
El producto inicial es el **motor técnico de simulación SAT**, no el sistema de trámite.

- **Incluye ahora:** interfaz web de prueba; APIs/web services; motor SAT para ítems 1, 3 y 4; mapas, matrices, resultados y dictamen técnico preliminar.
- **No incluye ahora:** radicación formal; workflow jurídico-administrativo; firma, notificaciones o pagos; decisión regulatoria definitiva; ítem 2 (grupo de baja potencia); ítem 5 (ESIM).
- **Principio de arquitectura:** el simulador queda desacoplado — hoy se prueba vía interfaz web; en fases futuras será consumido por plataformas de trámite, visores, gestores de espectro o sistemas externos (progresión SAT → API/MVP → PMP/MW).

### Diapositiva 3 — Arquitectura objetivo
Core de simulaciones con entradas normalizadas, módulos técnicos y salidas reutilizables.

**Diagrama de arquitectura (descripción del esquema):**
- Una **interfaz web de usuario** recibe tres flujos de entrada y los envía a un **núcleo de procesamiento tipo servidor**.
- Ese núcleo integra un módulo **SAT** (activo ahora), un módulo de utilidades (**uO**) y un módulo **PMP** (futuro), todo enmarcado en un bloque de procesamiento común.
- El núcleo se alimenta de fuentes externas: **Visor de Espectro, ICS Manager, MIRF/asignaciones UIT (Geo-NGeo) y cartografía.**
- La salida del núcleo alimenta el resultado final del sistema.

### Diapositiva 4 — Cobertura SAT inicial: ítems 1, 3 y 4
Se elimina ambigüedad: el primer alcance aplica solo a tres casos satelitales:

- **Ítem 1 / (i):** Estación terrena con características técnicas particulares. Ejemplos: telepuertos o gateway; estaciones con PIRE > 60 dBW. Evalúa compatibilidad, coordinación e interferencia para casos individuales.
- **Ítem 3 / (iii):** Estación formada por arreglo estructurado de antenas enlazadas a constelación No-GEO. Ejemplo: telepuerto con múltiples antenas dentro de radio de 250 m. Evalúa geometría temporal, agregación y métricas No-GEO.
- **Ítem 4 / (vi):** Estación de solo recepción por interés del PRST. Ejemplo: estaciones que usan únicamente enlace descendente espacio–tierra. Evalúa protección del receptor, calidad de enlace y entorno interferente.

**Referencia de origen de la clasificación (imagen ANE incluida en la diapositiva):**
La lámina reproduce un gráfico de la Agencia Nacional del Espectro (ANE) titulado *"Los permisos se solicitan conforme los tipos de estaciones terrenas requeridas por el asignatario"*, que clasifica 5 tipos de estación:

| Código | Tipo de estación | Ejemplo / condición asociada |
|---|---|---|
| (i) | Características técnicas particulares | Telepuertos o Gateway; estaciones con PIRE > 60 dBW |
| (ii) | Grupo de estaciones de baja potencia con características similares | Terminales fijos/móviles, VSAT, PIRE ≤ 60 dBW — "no protección, no interferencias" |
| (iii) | Arreglo estructurado de antenas enlazado a constelación No-GEO | Telepuerto con múltiples antenas dentro de radio de 250 m |
| (vi) | Solo recepción por interés del PRST | Estaciones que usan únicamente el enlace descendente (E-T) |
| (v) | Grupo de estaciones ESIM (Estación Terrena en Movimiento) con características similares | Cumplimiento de reglamentaciones aeronáuticas, marítimas y terrestres — "no protección, no interferencias" |

La selección para esta fase del proyecto es **(i), (iii) y (vi)**.

### Diapositiva 5 — Simulaciones y resultados esperados por caso
Cada simulación debe producir valores, márgenes, mapas y una recomendación técnica trazable.

| Caso | Simulaciones principales | Resultados esperados |
|---|---|---|
| Ítem 1 / (i) | Co-canal, canal adyacente, I/N, C/I, C/(N+I), PFD, área de coordinación, estaciones afectadas | Previable / condicionada / no previable; límites de PIRE/EIRP, bandas, condiciones y coordinación |
| Ítem 3 / (iii) | Visibilidad orbital, elevación/azimut, satélites visibles, agregación, No-GEO, EPFD preliminar y percentiles temporales | Riesgo No-GEO/GEO, estaciones/redes afectadas, margen temporal y restricciones de operación |
| Ítem 4 / (vi) | Enlace descendente, I/N, C/(N+I), disponibilidad, degradación de recepción y entorno interferente | Nivel de protección/riesgo, afectaciones recibidas, disponibilidad esperada y condiciones de instalación |

**Salida común a los tres casos:** JSON/API + reporte PDF/Excel + mapas + matriz de cumplimiento + lista de estaciones/redes consideradas + trazabilidad.

### Diapositiva 6 — Fases y tiempos estimados
Ruta recomendada para controlar alcance, riesgo técnico y presupuesto (modelo de 5 fases):

| Fase | Nombre | Duración | Contenido |
|---|---|---|---|
| F0 | Definición | 3–5 semanas | Reglas, datos, arquitectura, backlog y casos de prueba |
| F1 | MVP SAT | 4–6 meses | Interfaz de prueba, APIs y motor SAT básico para ítems 1, 3 y 4 |
| F2 | SAT institucional | +4–6 meses | No-GEO robusto, trazabilidad, piloto y validación con casos reales |
| F3 | PMP futuro | +4–6 meses | Sectores PMP, coexistencia y mapas |
| F4 | Microondas futuro | +3–5 meses | Enlaces PTP, perfiles y disponibilidad |

- **Hito ejecutivo:** al mes 5–6 debe existir un MVP demostrable con entrada de datos SAT, API funcional, mapas, estaciones afectadas y concepto preliminar.
- **Tiempo recomendado para SAT institucional:** 9 a 12 meses, validado para ítems 1, 3 y 4 con casos reales.

### Diapositiva 7 — Regulaciones y fuentes por fase
Cada fase usa reglas y fuentes trazables; la Fase 0 convierte la normativa en reglas ejecutables del simulador.

**Bloques de referencia normativa:**
- **Base nacional:** Resolución MinTIC 376 de 2022; CNABF vigente + notas CLM; Formatos técnicos ANE/MinTIC.
- **Base UIT:** RR Art. 5, 9, 11, 21 y 22; Apéndices 4 y 7; Recomendaciones UIT-R aplicables.
- **Fuentes operativas:** Visor de Espectro; ICS Manager/asignaciones; MIFR/MIRF, SNS/SNL, cartografía.

**Regulaciones/fuentes y uso por fase:**

| Fase | Regulaciones / fuentes | Uso en el simulador |
|---|---|---|
| F0 · Definición | Resolución 376, CNABF, RR Art. 5, Ap. 4 y Ap. 7 | Matriz normativa, campos obligatorios, reglas de elegibilidad y casos de prueba. |
| F1 · MVP SAT | CNABF, Visor/ICS, P.620, P.452, P.618, S.465/S.580 | Validación de banda, estaciones cercanas, área de coordinación e interferencia básica. |
| F2 · SAT institucional | RR Art. 21/22, S.1503, S.1323/S.1432, P.676/P.837/P.838/P.840, MIFR/SNS/SNL/GIMS | No-GEO robusto, EPFD preliminar/validable, degradación de enlace, trazabilidad y piloto. |
| F3 · PMP futuro | CNABF, P.452, P.1812, P.1546, P.2108 y recomendaciones F-series | Coexistencia punto-multipunto, cobertura, interferencia agregada y mapas de riesgo. |
| F4 · MW futuro | P.530, P.452, P.676, P.837/P.838 y recomendaciones F-series | Enlaces PTP, perfiles de trayecto, disponibilidad, desvanecimiento e interferencia. |

### Diapositiva 8 — Normativa que soporta los cálculos SAT
La matriz de salida debe mostrar valor calculado, margen, resultado y fuente normativa/técnica usada.

| Bloque temático | Normas / fuentes | Qué valida |
|---|---|---|
| Atribución y elegibilidad | CNABF vigente · RR Art. 5 · notas internacionales · notas nacionales CLM | ¿La banda y el servicio solicitado están permitidos? ¿El sentido del enlace es coherente? |
| Datos técnicos de entrada | Resolución 376 de 2022 · RR Apéndice 4 · formatos técnicos ANE/MinTIC | Campos obligatorios: coordenadas, PIRE/EIRP, G/T, antena, frecuencia, ancho de banda, satélite/red. |
| Área de coordinación | RR Art. 9 · RR Apéndice 7 · ITU-R P.620 · ITU-R SM.1448 | Contornos de coordinación, estaciones dentro del área crítica, distancias, azimuts y necesidad de coordinación. |
| Interferencia y propagación | ITU-R P.452 · P.618 · P.676 · P.837 · P.838 · P.840 · S.465 · S.580 · S.1323 · S.1432 | I/N, C/I, C/(N+I), PFD, canal adyacente, degradación de enlace, disponibilidad y márgenes. |
| No-GEO / arreglos | RR Art. 22 · ITU-R S.1503 · S.1528 · MIFR/MIRF · SNS/SNL · GIMS | Satélites visibles, geometría temporal, agregación, percentiles y EPFD preliminar/validable. |

**Salida esperada:** criterio · valor calculado · umbral · margen · cumple/no cumple · fuente normativa/técnica · versión de datos utilizada.

### Diapositiva 9 — Personal requerido
Equipo mixto; varias dedicaciones son parciales y cambian por fase.

| Rol | Dedicación (FTE) | Responsabilidad principal |
|---|---|---|
| Gerente / líder de proyecto | 0.3–0.5 | Gobierno, riesgos, cronograma y coordinación |
| Arquitecto de solución | 0.5–0.7 | Arquitectura modular, APIs, seguridad y escalabilidad |
| Experto RF satelital | 0.8–1.0 | Modelos I/N, C/I, PFD, EPFD, escenarios SAT |
| Regulatorio UIT / licencias | 0.4–0.7 | Reglas UIT/nacionales y matriz de cumplimiento |
| Ingeniero de simulación | 0.8–1.0 | Motor numérico, escenarios y validación técnica |
| Backend / APIs | 1–2 | Servicios, datos, motor y trazabilidad |
| Frontend / UX | 1 | Interfaz web de prueba y visualización |
| GIS / datos espaciales | 0.5–0.8 | PostGIS, mapas, contornos y cartografía |
| QA técnico | 0.5–0.8 | Pruebas funcionales y validación con casos reales |

**Equipo promedio recomendado para SAT institucional:** 6 a 9 personas.

### Diapositiva 10 — Costos de referencia
Rangos ejecutivos en USD; deben cerrarse luego de Fase 0 y casos de prueba.

| Escenario | Tiempo | Equipo | Desarrollo | Herramientas |
|---|---|---|---|---|
| MVP SAT inicial | 4–6 meses | 5–6 | USD 180k–300k | USD 10k–50k |
| SAT institucional recomendado | 9–12 meses | 7–9 | USD 400k–750k | USD 120k–400k |
| SAT No-GEO avanzado | 12–18 meses | 9–12 | USD 750k–1.3M | USD 300k–700k |
| Expansión PMP | +4–6 meses | 4–6 | USD 180k–350k | Según herramienta |
| Expansión microondas | +3–5 meses | 4–5 | USD 120k–280k | Según herramienta |

**Presupuesto sugerido para iniciar:** Fase 0 + MVP SAT, priorizando motor propio auditable y herramientas comerciales solo para validación selectiva.

### Diapositiva 11 — Decisión ejecutiva propuesta
Arrancar con SAT para ítems 1, 3 y 4, pero contratar arquitectura modular desde el primer día.

1. **Aprobar Fase 0** — 3–5 semanas para cerrar reglas, datos, arquitectura, backlog, costos definitivos y casos de prueba.
2. **Construir MVP SAT** — 4–6 meses con API, interfaz de prueba, simulación y reporte técnico para ítems 1, 3 y 4.
3. **Escalar por resultados** — Institucionalizar SAT y habilitar PMP/MW cuando el core esté validado.

**Condiciones críticas de éxito:** datos confiables de estaciones existentes, criterios UIT/nacionales claros, casos reales de validación y decisión temprana sobre herramientas comerciales.

**Solicitud de decisión:** autorizar fase de definición y prototipo SAT para obtener una demo funcional y un presupuesto cerrado de la fase institucional.

---

## 3. Presentación 2 — "Sistema de previabilidad de licencias satelitales" (junio 2026)

Versión más reciente y refinada de la propuesta ejecutiva (8 láminas), con cifras en USD y COP.

### Diapositiva 1 — Portada
- **Título:** Sistema de previabilidad de licencias satelitales — 3 tipos de estación.
- Simulación RF/GIS/No-GEO. Fases, alcance, tiempos, equipo y costos estimados. Dictamen auditable.
- Fecha: **junio 2026**. Valores referenciales en USD y COP, aproximados a **4.000 COP/USD**.

### Diapositiva 2 — Alcance funcional propuesto
El sistema transforma una solicitud técnica en un concepto preliminar trazable para autoridad y solicitante.

| Tipo de estación | Qué evalúa |
|---|---|
| 1. Estación particular | Validación de parámetros especiales: EIRP, patrón de antena, banda, ubicación, coordinación y condiciones técnicas. |
| 2. Arreglo No-GEO | Simulación dinámica: visibilidad orbital, haces, handover, agregación, EPFD/PFD y protección GSO/No-GSO. |
| 3. Solo recepción | Evaluación de protección del receptor: entorno de interferencia, C/(N+I), margen y disponibilidad del enlace. |

**Motor común:** base de estaciones existentes + GIS + bandas + reglas UIT/nacionales + motor de interferencia + reportes.

**Resultado posible:** previable / previable condicionada / no previable / requiere coordinación / información insuficiente.

### Diapositiva 3 — Fases ejecutivas del proyecto
Ruta recomendada para entregar valor temprano sin subestimar el componente No-GEO y regulatorio. Esta versión usa **7 fases (0 a 6)**:

| Fase | Nombre | Duración |
|---|---|---|
| 0 | Definición técnica y regulatoria | 1 mes |
| 1 | Datos, solicitudes y base GIS | 1.5 meses |
| 2 | Motor RF básico | 2 meses |
| 3 | GIS y área de coordinación | 1.5 meses |
| 4 | No-GEO / arreglos de antenas | 2.5 meses |
| 5 | Decisión, reportes y trazabilidad | 1.5 meses |
| 6 | Validación, piloto y capacitación | 2 meses |

- **Cronograma recomendado:** 10 a 12 meses. Con paralelización agresiva: 8 a 9 meses (con mayor riesgo de retrabajo).
- **Hitos de madurez del producto:**
  - **MVP:** 4–6 meses
  - **Institucional:** 8–12 meses
  - **Avanzado:** 12–18 meses

### Diapositiva 4 — Entregables por etapa
Enfoque de dos etapas: demostrar valor rápido y luego robustecer para uso institucional.

| Etapa 1 — MVP validable (4 a 6 meses) | Etapa 2 — Plataforma institucional (5 a 8 meses adicionales) |
|---|---|
| Captura y validación de solicitudes | No-GEO, arreglos y simulación temporal |
| Base inicial de estaciones existentes | Agregación y percentiles |
| I/N, C/I, PFD y canal adyacente | Motor de reglas UIT/nacionales |
| Mapas básicos y estaciones afectadas | Trazabilidad, auditoría y roles |
| Dictamen preliminar y reporte PDF | Reportes para autoridad y solicitante |
| — | Piloto, validación y capacitación |

- **Objetivo Etapa 1:** probar metodología y casos reales.
- **Objetivo Etapa 2:** operación institucional confiable.

### Diapositiva 5 — Personal requerido
Equipo mixto: regulación + RF/satelital + simulación + software + GIS + validación.

| Rol | Dedicación |
|---|---|
| Gerencia / PM | 0.3–0.5 FTE |
| Arquitectura de solución | 0.5–0.7 FTE |
| RF / satelital | 0.8–1.0 FTE |
| Regulatorio UIT | 0.4–0.7 FTE |
| Simulación | 0.8–1.0 FTE |
| Backend | 1–2 FTE |
| Frontend | 1 FTE |
| GIS / datos | 0.5–0.8 FTE |
| DevOps / seguridad | 0.3–0.5 FTE |
| QA / validación | 0.5–0.8 FTE |

**Equipo recomendado:** 6–9 personas promedio. **Esfuerzo estimado:** 28–47 persona-mes.

### Diapositiva 6 — Costos estimados del desarrollo
Rangos de orden de magnitud para presupuesto preliminar. No incluyen IVA, interventoría, ni adquisición formal de datos externos.

| Escenario | USD | COP | Tiempo | Alcance |
|---|---|---|---|---|
| MVP técnico | USD 180k–320k | COP 720–1.280 M | 4–6 meses | Probar metodología, motor RF básico, reportes simples |
| Institucional | USD 450k–850k | COP 1.800–3.400 M | 8–12 meses | Motor RF/GIS, No-GEO intermedio, trazabilidad y piloto |
| Avanzado | USD 900k–1.8M | COP 3.600–7.200 M | 12–18 meses | No-GEO robusto, EPFD, integraciones, auditoría fuerte |

*Nota: costos estimados con equipo local/regional especializado. Una fábrica internacional o integración regulatoria completa puede elevar estos rangos.*

### Diapositiva 7 — Costos de herramientas comerciales
Estrategia: motor propio + validación selectiva con herramientas reconocidas, evitando comprar una suite completa al inicio.

| Paquete de herramientas | Costo | Perfil de uso |
|---|---|---|
| Sat-Coord/SatMaster + open source | USD 10k–50k | Austera / MVP |
| Visualyse Coordinate/Professional + STK/HTZ selectivo | USD 150k–400k | Institucional |
| Visualyse EPFD + STK Premium + soporte especializado | USD 300k–700k | No-GEO avanzada |
| SPECTRA/mySPECTRA + integración institucional | USD 700k–3M+ | Suite regulatoria integral |

**Recomendación presupuestal inicial:** no comprar todo. Reservar USD 150k–400k para herramientas de validación si la plataforma debe soportar decisiones institucionales.

### Diapositiva 8 — Decisión recomendada para presentar hoy
Proponer un proyecto por etapas con control de riesgo técnico y entregables verificables: **Contratar MVP → Validar con casos reales → Escalar institucional.**

- **Solicitud concreta:** aprobar una fase 0 de 3–5 semanas para cerrar alcance, criterios UIT/nacionales, datos disponibles, arquitectura y presupuesto final.
- **Presupuesto base sugerido:** plan de 12 meses: USD 450k–850k de desarrollo + USD 150k–400k potenciales en herramientas comerciales.
- **Mensaje ejecutivo:** *"No estamos comprando una simulación; estamos construyendo un expediente técnico automático para soportar predecisiones de licencia."*

---

## 4. Comparación entre las dos presentaciones ejecutivas

| Aspecto | Presentación 1 (Core de simulaciones) | Presentación 2 (Sistema de previabilidad, jun-2026) |
|---|---|---|
| N.º de láminas | 11 | 8 |
| Modelo de fases | 5 fases (F0–F4) | 7 fases (0–6) |
| Duración total institucional | 9–12 meses | 10–12 meses (8–9 con paralelización agresiva) |
| Costo MVP | USD 180k–300k | USD 180k–320k |
| Costo institucional | USD 400k–750k | USD 450k–850k (COP 1.800–3.400 M) |
| Costo avanzado/No-GEO | USD 750k–1.3M | USD 900k–1.8M (COP 3.600–7.200 M) |
| Equipo | 6–9 personas | 6–9 personas (28–47 persona-mes) |
| Moneda | Solo USD | USD y COP |
| Incluye tabla de herramientas comerciales | No | Sí (Sat-Coord/SatMaster, Visualyse, STK, SPECTRA) |
| Incluye diagrama de arquitectura técnica | Sí (imagen) | No |
| Incluye referencia visual ANE de tipos de estación | Sí (imagen) | No (solo texto) |

**Lectura conjunta:** la Presentación 2 es una evolución de la Presentación 1 — mantiene el mismo alcance (ítems (i), (iii), (vi)), el mismo tamaño de equipo y órdenes de magnitud de costo similares, pero reestructura las fases (de 5 a 7, con mayor granularidad en la parte de datos/GIS/No-GEO), añade cifras en pesos colombianos, e incorpora un desglose específico de costos de herramientas comerciales de coordinación satelital que no aparecía antes.

---

## 5. Síntesis normativa transversal (válida para las tres fuentes)

Todas las fuentes coinciden en que el motor de simulación se apoya en tres capas normativas/de datos:

1. **Normativa nacional colombiana:** Resolución MinTIC 376 de 2022 (clasificación de estaciones y requisitos técnicos) y CNABF vigente de la ANE (atribución de bandas, servicio y sentido del enlace).
2. **Normativa internacional UIT:** Reglamento de Radiocomunicaciones — Artículos 5 (atribución), 9 y 21 (coordinación y límites PFD), 11 (notificación), 22 (límites EPFD para No-GEO); Apéndices 4 (datos mínimos) y 7 (contornos de coordinación); y Recomendaciones UIT-R de la serie P (propagación: P.452, P.618, P.620, P.676, P.837, P.838, P.840) y serie S (satélites: S.465, S.580, S.1323, S.1428, S.1432, S.1503, S.1528).
3. **Fuentes de datos operativos:** Visor de Espectro e ICS Manager (ANE, nacional); MIFR/MIRF, SNS, SNL, GIMS y BR IFIC (UIT, internacional); y capas cartográficas/modelos de terreno para el componente geográfico.

El resultado de cualquier análisis, en cualquiera de los tres casos, siempre se expresa como uno de estos cinco estados: **previable · previable condicionada · no previable · requiere coordinación · información insuficiente**, acompañado de trazabilidad completa (fuente normativa y versión de datos usados en cada cálculo).
