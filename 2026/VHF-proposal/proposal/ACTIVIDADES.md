# Actividades del Proyecto — Asignación por Estudiante (9 meses)

## Estudiantes y disponibilidad

| Estudiante | Contrato | Disponibilidad | Habilidades principales |
|---|---|---|---|
| **David Ramírez Betancourth** | 9 meses | Meses 1–9 | Python, C, C++, sistemas embebidos (ESP-IDF, Raspberry Pi, Jetson Nano), preproceso SDR, programación con agentes |
| **Oscar Andrés Gutiérrez Estepa** | 9 meses | Meses 1–9 | Python, C, DSP con ML/DL, calibración de equipos RF, programación con agentes |
| **Cristian David Dorado Gómez** | 2 meses | Meses 1–2 | Python, C, DSP con ML/DL, preproceso SDR, programación con agentes |

---

## Objetivo 1: Adquisición, procesamiento y almacenamiento de datos espectrales

### Actividad 1.1: Definir escenarios y requisitos para el monitoreo del espectro aeronáutico

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)
**Soporte:** Cristian David Dorado Gómez (meses 1–2)

**Tareas:**

- Identificación de frecuencias y servicios aeronáuticos objetivo.
- Definición de variables de RF y parámetros espectrales relevantes.
- Caracterización de escenarios de interferencia e intermodulación.
- Definición de requisitos técnicos para la adquisición y el almacenamiento.

**Justificación de asignación:** Oscar posee experiencia en calibración de equipos RF y DSP, lo que lo qualifica para la caracterización espectral. Cristian apoya en la revisión bibliográfica y documentación durante sus 2 meses.

**Resultados esperados:** Documento de especificaciones técnicas que describa los escenarios de RF y los requisitos de monitoreo.

---

### Actividad 1.2: Implementar la infraestructura SDR y capturar experimentalmente señales de RF

**Responsable:** David Ramírez Betancourth (líder)

**Tareas:**

- Configuración de plataformas SDR, Raspberry Pi y NVIDIA Jetson.
- Integración de hardware de adquisición de RF y antenas.
- Desarrollo de rutinas de captura y almacenamiento de señales IQ.
- Validación de la estabilidad de la adquisición y la consistencia espectral.

**Justificación de asignación:** David tiene experiencia directa en sistemas embebidos (ESP-IDF, Raspberry Pi, Jetson Nano) y preproceso SDR, habilidades esenciales para el montaje y configuración del hardware.

**Resultados esperados:** Infraestructura SDR funcional para la adquisición y el almacenamiento distribuido de RF.

---

### Actividad 1.3: Generar representaciones espectrales y organizar el conjunto de datos

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)
**Soporte:** Cristian David Dorado Gómez (mes 2)

**Tareas:**

- Filtrado y normalización de las señales de RF capturadas.
- Generación de espectrogramas y representaciones de tiempo-frecuencia.
- Definición de criterios de segmentación y etiquetado.
- Organización estructurada y almacenamiento del conjunto de datos espectrales.

**Justificación de asignación:** Oscar aporta su experiencia en DSP para el preprocesamiento y generación de representaciones espectrales. Cristian apoya en tareas de filtrado y normalización durante su segundo mes.

**Resultados esperados:** Conjunto de datos espectrales estructurado y optimizado para entrenamiento y validación.

---

### Actividad 1.4: Desarrollar estrategias de entrenamiento para escenarios con información espectral limitada

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)
**Soporte:** David Ramírez Betancourth

**Tareas:**

- Análisis estadístico de distribuciones espectrales y eventos de interferencia.
- Implementación de técnicas de aumentación de datos de RF.
- Definición de criterios de selección de eventos relevantes.
- Desarrollo de estrategias de entrenamiento adaptativas y robustas.
- Evaluación preliminar bajo condiciones de RF dinámicas y degradadas.

**Justificación de asignación:** Oscar lidera por su especialización en ML/DL aplicado a DSP. David apoya en la implementación de rutinas de procesamiento en Python/C.

**Resultados esperados:** Modelos inteligentes robustos capaces de operar bajo condiciones de baja SNR y entornos de RF altamente variables.

---

## Objetivo 2: Framework inteligente de análisis espectral

### Actividad 2.1: Desarrollar arquitecturas inteligentes para el análisis espectral

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)

**Tareas:**

- Diseño de arquitecturas compactas para análisis espectral.
- Evaluación bajo escenarios de baja SNR y alta variabilidad espectral.
- Comparación entre modelos ligeros y modelos baseline.
- Optimización de robustez frente a escenarios desbalanceados.
- Validación preliminar de desempeño espectral.

**Justificación de asignación:** Oscar lidera el diseño de modelos de ML/DL por su experiencia en DSP con aprendizaje profundo.

**Resultados esperados:** Modelos inteligentes compactos para monitoreo espectral aeronáutico y framework inicial de clasificación espectral robusta.

---

### Actividad 2.2: Integrar restricciones físicas y variables espectrales en los procesos de entrenamiento y validación

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)
**Soporte:** David Ramírez Betancourth

**Tareas:**

- Definición de restricciones y variables espectrales.
- Integración de parámetros espectrales en pipelines de entrenamiento.
- Evaluación de coherencia espectral de las predicciones.
- Comparación entre modelos convencionales y modelos informados por restricciones espectrales.
- Evaluación bajo escenarios degradados de RF.

**Justificación de asignación:** Oscar combina conocimiento de DSP y ML para integrar restricciones físicas en los modelos. David apoya con la implementación de pipelines en código.

**Resultados esperados:** Framework inteligente con consistencia espectral y mejora de robustez bajo condiciones degradadas.

---

### Actividad 2.3: Desarrollar mecanismos de interpretabilidad y validar la consistencia espectral de las predicciones

**Responsable:** Oscar Andrés Gutiérrez Estepa (líder)
**Soporte:** David Ramírez Betancourth

**Tareas:**

- Desarrollo de mecanismos post-hoc de interpretabilidad.
- Visualización de regiones espectrales relevantes.
- Evaluación de consistencia entre predicciones y comportamiento espectral.
- Validación bajo escenarios de interferencia y variabilidad espectral.
- Consolidación de análisis interpretativos para soporte operacional.

**Justificación de asignación:** Oscar lidera la interpretabilidad de modelos ML/DL. David apoya en la visualización y generación de reportes.

**Resultados esperados:** Sistema interpretable para monitoreo espectral aeronáutico y validación de coherencia entre predicciones y comportamiento espectral.

---

## Objetivo 3: Despliegue en plataformas SDR embebidas y edge computing

### Actividad 3.1: Optimizar los modelos inteligentes para su implementación en plataformas SDR embebidas

**Responsable:** David Ramírez Betancourth (líder)

**Tareas:**

- Optimización de modelos inteligentes para despliegue embebido.
- Aplicación de técnicas de quantization y pruning.
- Evaluación de complejidad computacional y latencia.
- Reducción de consumo de memoria y recursos de procesamiento.
- Validación preliminar sobre plataformas embebidas.

**Justificación de asignación:** David lidera por su experiencia en sistemas embebidos (Jetson Nano, Raspberry Pi) y optimización de modelos para hardware de borde.

**Resultados esperados:** Modelos optimizados compatibles con plataformas SDR embebidas y reducción de complejidad computacional para inferencia edge.

---

### Actividad 3.2: Desplegar el sistema de monitoreo distribuido en plataformas SDR y dispositivos de edge computing

**Responsable:** David Ramírez Betancourth (líder)

**Tareas:**

- Integración en plataformas Raspberry Pi y NVIDIA Jetson.
- Implementación de procesamiento espectral distribuido.
- Evaluación de desempeño operacional en tiempo real.
- Validación de estabilidad bajo escenarios degradados.
- Consolidación de arquitectura SDR-edge distribuida.

**Justificación de asignación:** David lidera por su dominio de ESP-IDF, Raspberry Pi y Jetson Nano, esencial para el despliegue embebido distribuido.

**Resultados esperados:** Arquitectura distribuida para monitoreo espectral inteligente e integración funcional entre SDR y edge computing.

---

### Actividad 3.3: Validar operacionalmente el sistema y articular los procesos técnicos y regulatorios

**Responsable:** David Ramírez Betancourth (líder, validación de hardware)
**Co-responsable:** Oscar Andrés Gutiérrez Estepa (análisis de resultados)

**Tareas:**

- Definición de protocolos de validación operacional.
- Coordinación técnica y regulatoria con ANE.
- Gestión de autorizaciones para pruebas controladas en entornos representativos.
- Evaluación experimental de escenarios de interferencia e intermodulación.
- Validación de desempeño operacional del sistema SDR-edge.
- Consolidación de resultados interdisciplinarios.
- Documentación técnica y metodológica de validación.

**Justificación de asignación:** David valida el funcionamiento del hardware embebido; Oscar analiza los resultados espectrales y verifica la coherencia de los modelos. Trabajo conjunto para la validación integral.

**Resultados esperados:** Validación funcional del sistema de monitoreo inteligente en entornos representativos y fortalecimiento del nivel de madurez tecnológica del prototipo hacia escenarios TRL 6.

---

## Cronograma (9 meses, trabajo paralelo)

Los tres estudiantes trabajan en paralelo. Cristian solo participa en los meses 1 y 2.

```
Actividad                                  M1   M2   M3   M4   M5   M6   M7   M8   M9
───────────────────────────────────────── ──── ──── ──── ──── ──── ──── ──── ──── ────
1.1 Definir escenarios y requisitos       [DC] [DC]
1.2 Implementar infraestructura SDR        [D]  [D]  [D]
1.3 Generar representaciones espectrales        [OC] [O]  [O]
1.4 Estrategias entrenamiento                   [ ]  [O]  [O]  [O]
2.1 Arquitecturas IA para análisis espectral         [ ]  [O]  [O]  [O]
2.2 Integrar restricciones físicas                         [ ]  [O]  [O]  [O]
2.3 Interpretabilidad y consistencia                            [ ]  [O]  [O]  [O]
3.1 Optimizar modelos para embebido                      [ ]  [D]  [D]  [D]
3.2 Desplegar sistema distribuido                              [ ]  [D]  [D]  [D]
3.3 Validación operacional                                          [ ]  [DO] [DO]
───────────────────────────────────────── ──── ──── ──── ──── ──── ──── ──── ──── ────
```

**Leyenda:**
- **D** = David Ramírez Betancourth
- **O** = Oscar Andrés Gutiérrez Estepa
- **C** = Cristian David Dorado Gómez (solo meses 1–2)
- **DC** = David + Cristian trabajando en paralelo
- **OC** = Oscar + Cristian trabajando en paralelo
- **DO** = David + Oscar trabajando en conjunto

### Resumen de carga por estudiante

| Estudiante | Meses activos | Actividades lideradas | Actividades de soporte |
|---|---|---|---|
| David Ramírez Betancourth | 1–9 (9 meses) | 1.2, 3.1, 3.2, 3.3 | 1.4, 2.2, 2.3 |
| Oscar Andrés Gutiérrez Estepa | 1–9 (9 meses) | 1.1, 1.3, 1.4, 2.1, 2.2, 2.3 | 3.3 |
| Cristian David Dorado Gómez | 1–2 (2 meses) | — | 1.1, 1.3 |

### Justificación del cronograma

El cronograma original de 18 meses se comprime a 9 meses mediante trabajo paralelo:

- **Meses 1–2 (3 estudiantes):** Se ejecutan en paralelo la definición de escenarios (1.1), el montaje de infraestructura SDR (1.2) y el inicio del preprocesamiento (1.3). Cristian apoya en ambas líneas de trabajo.
- **Meses 3–4 (2 estudiantes):** David completa la infraestructura SDR mientras Oscar avanza en representaciones espectrales y estrategias de entrenamiento.
- **Meses 5–6 (2 estudiantes):** Oscar desarrolla las arquitecturas IA (2.1) e integra restricciones físicas (2.2); David inicia la optimización para embebido (3.1).
- **Meses 7–8 (2 estudiantes):** Oscar trabaja en interpretabilidad (2.3); David despliega el sistema distribuido (3.2).
- **Mes 9 (2 estudiantes):** Validación operacional conjunta (3.3) con ambos estudiantes.
