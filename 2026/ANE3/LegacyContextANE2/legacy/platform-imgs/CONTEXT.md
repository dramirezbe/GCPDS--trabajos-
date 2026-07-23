# Image Context for AI

This directory contains reference PNG screenshots for the ANE spectral sensing platform. The UI language is Spanish, the viewport is desktop-width, and the product domain is radio-frequency spectrum sensing, sensor management, real-time monitoring, measurement campaigns, alerts, and administration.

## Global Visual System

- Brand: ANE, shown with a gold/orange Colombian-style emblem above large `ANE` letters and a small yellow-blue-red bar.
- Layout: most authenticated screens use a fixed left sidebar, white or light-gray content surfaces, and dense operational dashboard layouts.
- Sidebar navigation: `Inicio`, `Dispositivos`, `Monitoreo`, `Campanas`, `Alertas`, `Configuracion`; bottom user block `Administrador`, plus `Ayuda` and red `Cerrar sesion`.
- Primary color: vivid orange for active navigation, primary actions, charts, and campaign headers.
- Secondary colors: blue for hardware/configuration actions, green for success/online states, red for alerts/errors/offline and destructive actions, gray for neutral metadata.
- Maps: several screens use Leaflet/OpenStreetMap tiles centered on Colombia and northern South America.
- Data visuals: circular summary charts, RF spectrum line charts in dBm vs MHz, and blue waterfall/heatmap bands with bright vertical signal traces.
- Component style: white cards with subtle borders/shadows, small rounded badges, toolbar icon buttons, date inputs, tabs/chips, select fields, sliders, and tables.

## Image Catalog

### `auth.png` - Microsoft Azure login

- Size: 1920 x 936.
- Purpose: primary authentication entry screen.
- Visual description: a warm peach-to-orange gradient background with a centered white rounded card. The card contains the ANE emblem/logo, subtitle `Plataforma de sensado espectral`, a divider, and a single SSO action labeled `Ingresar con Microsoft Azure`.
- Important details: includes a small grid/Microsoft-style icon to the left of the login action and an underlined link `Acceso Administrativo / Legacy` below it.
- AI interpretation: use this as the modern SSO login state.

### `auth-legacy.png` - legacy username/password login

- Size: 1920 x 936.
- Purpose: fallback administrative login screen.
- Visual description: same peach gradient background and centered ANE card as `auth.png`, but with two form fields: `Usuario` and `Escribe la contrasena`; the password field includes an eye visibility icon.
- Important details: the main button is a brown/orange full-width CTA labeled `Ingresar en la plataforma`, followed by a text link `Volver a Ingreso Microsoft`.
- AI interpretation: use this as the non-SSO/legacy login flow.

### `main.png` - home dashboard

- Size: 1920 x 936.
- Purpose: authenticated landing dashboard for the platform.
- Visual description: full-screen map background over Colombia/northern South America with a left ANE sidebar. A large centered title reads `Bienvenido a ANE | Plataforma de Sensado Espectral`.
- Main content: a large white `Estadisticas Generales` panel with two donut charts:
  - `Campanas`: 211 total; programmed 0, running 0, completed 211, canceled 0.
  - `Dispositivos`: 10 total; online 3, occupied 1, delay 1, offline 5, error 0.
- Lower content: three navigation cards for `Dispositivos`, `Monitoreo`, and `Campanas`, each with a short description and orange link.
- AI interpretation: this is the overview/dashboard state and shows the main information architecture.

### `devices.png` - sensors map and list

- Size: 1920 x 1626.
- Purpose: sensor/device inventory view.
- Visual description: left sidebar active on `Dispositivos`; next to it is a scrollable `Sensores` list; the rest of the screen is a Leaflet map.
- Main content: each sensor entry shows a radio/signal icon, sensor name such as ANE6, ANE7, ANE8, ANE10, ANE1, etc., optional description, coordinates, status badge (`Ocupado`, `Offline`, `Online`), and MAC address.
- Map details: the map is zoomed to the Americas, with a green clustered marker near Colombia. Standard Leaflet zoom controls appear at top left.
- AI interpretation: use this as the device management/geolocation screen. It emphasizes inventory status plus geographic placement.

### `realtime.png` - real-time monitoring and acquisition

- Size: 1920 x 1237.
- Purpose: live spectrum acquisition and monitoring.
- Visual description: left sidebar active on `Monitoreo`; a pale green acquisition configuration panel occupies the left content column; the right area contains the live RF visualization.
- State: a green status card says `Monitoreo Activo`, sensor `ANE2`, 512 frequency points. A red banner on the chart side says `ADQUIRIENDO ESPECTRO - ANE2`, with latitude, longitude, and altitude.
- Controls: sensor select, port/antenna select (`Puerto 1 - FM (78-128 MHz)`), `Crear campana`, frequency center/span fields, LNA/VGA gain sliders, antenna amp checkbox, RBW/VBW selects, frequency filter checkbox, remaining time, and red `Detener Adquisicion` button.
- Data visualization: the top chart is `Espectro de Frecuencias`, an orange dBm line with many sharp peaks between roughly 88 and 107 MHz. The bottom visualization is a blue waterfall heatmap with bright cyan/green/yellow vertical signal lines.
- AI interpretation: use this as the active live monitoring/acquisition state.

### `campaign.png` - campaigns archive and replay

- Size: 1920 x 4096.
- Purpose: campaign listing plus selected campaign analysis/replay.
- Visual description: left sidebar active on `Campanas`; a tall scrollable campaign list occupies the left panel, while the selected campaign visualization fills the right.
- Left panel: summary counts show programmed 0, running 0, finished 212, canceled 0, total 212. Contains a collapsible `Filtros` row, paginated campaign cards, eye/delete icons, campaign metadata, and an orange `Programar campana` button.
- Selected campaign: orange header for `Clean_db_unal_9h` with badge `#278`, controls for `Individual`, `Combinado`, `Sensor: ANE2`, `Info`, download, and close.
- Main chart: `Espectro de Frecuencias` with multi-sensor colored line traces and a legend for ANE2, ANE9, ANE4, ANE7, ANE1, ANE5, and ANE3. A replay/time strip shows date/time, frame `6 / 270`, play/step controls, scrubber, and speed `1x (1s)`.
- Waterfall: blue heatmap below the spectrum chart with vertical frequency activity bands.
- AI interpretation: use this as the historical measurement campaign analysis screen, including comparison mode and replay controls.

### `campaign-detailed.png` - campaign scheduling modal

- Size: 1920 x 926.
- Purpose: create/program a new measurement campaign from the campaigns section.
- Visual description: the `Campanas` page is dimmed under a large centered modal titled `Programar campana`. The left sidebar remains visible in the background with `Campanas` active, and the map remains visible behind the overlay.
- Modal layout: the form is split into a wide left configuration column and a narrower right device-selection column. A close `X` appears in the top-right corner.
- Campaign form: includes `Nombre de la campana`, start and end date pickers, acquisition frequency select (`Cada 2 minutos`), start and finish time fields, and helper text explaining that measurement minutes must match the chosen interval.
- Spectral configuration: section `Configuracion espectral` includes a presets select (`Personalizado`), central frequency field (`97.5 MHz`), span/sample rate field (`20 MHz`), LNA gain, and VGA gain controls lower in the scrollable form.
- Device selection: right panel `Seleccionar dispositivos para la campana` lists sensors such as ANE6 and ANE7 with MAC addresses, status markers (`busy`, `offline`), checkboxes, and text indicating `Se han seleccionado 0 dispositivos`.
- Footer actions: bottom sticky footer contains `Cancelar` and a pale orange primary button `Programar campana`, which appears disabled or low-emphasis because no devices are selected.
- AI interpretation: use this as the campaign creation/scheduling modal state, especially for date/time planning, device assignment, and RF acquisition parameter setup.

### `warnings.png` - alert panel overview

- Size: 1920 x 936.
- Purpose: anomaly/compliance alert dashboard.
- Visual description: left sidebar active on `Alertas`; page title `Panel de Alertas` and subtitle about monitoring anomalies in devices and regulatory compliance. The background is a Leaflet map over Colombia/Venezuela/Guyana.
- Layout: two main columns:
  - `Alertas de Sensores` with a red badge count `8`.
  - `Campanas Fuera de Parametros` with an orange/neutral badge count `0`.
- Sensor alerts: filter chips for `Hoy (Tiempo Real + Historial)` and `Historico (30 dias)`, date picker, alert cards for sensors such as ANE6, ANE7, ANE8, ANE5, ANE1, badges like `Offline` and `Temperatura Alta`, MAC addresses, timestamps, and pagination.
- Campaign alerts: filter chips `Hoy` and `Todas`, date picker, and an empty-state card with a green check and text `No hay campanas fuera de parametros hoy`.
- AI interpretation: use this as the alert overview screen with current and historical alert filtering.

### `warnings-detailed.png` - alert detail modal

- Size: 1920 x 1314.
- Purpose: detail drill-down for one sensor alert.
- Visual description: same alert dashboard dimmed under a centered modal. Modal header is pale red and reads `Detalle de Alerta: ANE6` with a warning icon and close button.
- Modal content: top metadata section shows `Estado / Tipo`, `27 alertas hoy (Ultima: Temperatura Alta), Temperatura Alta (77.1C)`, and MAC address `2c:cf:67:51:1b:9b`.
- History: table `HISTORIAL DE ALERTAS (27)` with columns date/time, type, and description; repeated `Temperatura Alta` badges and temperature values around 75-78C.
- Logs: dark terminal-style panel `LOGS DEL SISTEMA (TIEMPO REAL)` with HTTP GET/POST log lines.
- Metrics: four bottom metric cards for CPU promedio, RAM, disk, and temperature, e.g. 20.8%, 6.1%, 25.6%, and 77.1C.
- AI interpretation: use this as the modal/detail state for alert inspection and diagnostics.

### `configurations.png` - administration/configuration page

- Size: 1920 x 2400.
- Purpose: administrative setup for antennas, sensors, users, general system settings, and sensor unlocking.
- Visual description: left sidebar active on `Configuracion`; page title `Configuracion`; a large gray page background with white administration cards.
- Top row: `Antenas` card on the left and `Sensores` card on the right.
  - Antennas include FM, TDT, VHF/UHF, and >2GHz with type, frequency range, gain, description, delete icons, and orange `Agregar`.
  - Sensors show registered count 10, active 10, inactive 0, blue `+ Agregar`, and `Ver Todos los Sensores`.
- Middle section: `Usuarios` table with total users 10, administrators 3, technicians 7, green `Nuevo Usuario`, role badges, status badges, and edit/delete icons.
- Bottom section: `Configuracion General` with backend/frontend ports, database PostgreSQL, realtime acquisition time limit, frequency tolerance inputs; and `Desbloquear Sensor` with a select field for occupied sensors.
- AI interpretation: use this as the admin settings and user/asset management screen.

### `help.png` - help/manuals page

- Size: 1920 x 950.
- Purpose: help center and documentation entry point.
- Visual description: left sidebar active via the bottom `Ayuda` item; main title `Ayuda`.
- Content: two large side-by-side cards:
  - `Manual de Software`, with topics `Guia de Inicio Rapido`, `Gestion de Dispositivos`, `Monitoreo de Espectro`, `Campanas de Medicion`, `API y Integracion`, and an orange `Ver Manual Completo` button.
  - `Manual de Hardware`, with topics `Especificaciones de Sensores`, `Guia de Instalacion`, `Configuracion de Antenas`, `Mantenimiento`, `Solucion de Problemas`, and a blue `Ver Manual Completo` button.
- Footer help band: `Necesitas mas ayuda?`, support email `soporte@ane.gov.co`, API docs `docs.ane.gov.co`, and version `ANE v1.0.0`.
- AI interpretation: use this as the documentation/help hub.

## Recommended AI Usage

- Treat these images as product reference screenshots, not final production copy.
- Preserve the Spanish UI labels when generating UI, but normalize accents as needed depending on the codebase text conventions.
- Keep the platform feeling operational and data-heavy: maps, tables, status badges, filters, charts, and form controls are central.
- When generating new screens, match the left sidebar, ANE branding, orange active state, light neutral backgrounds, and compact dashboard density.
- For charts, use RF domain language: frequency in MHz, power in dBm, spectrum traces, waterfall heatmaps, sensors, antennas, campaigns, and acquisition parameters.
