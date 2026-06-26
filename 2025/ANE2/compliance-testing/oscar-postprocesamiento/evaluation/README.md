# Evaluation

Aqui vive todo lo que no forma parte del flujo operativo del servidor:

- benchmark offline
- pruebas unitarias e integracion
- scripts manuales
- reportes JSON
- graficas

## Estructura

- `benchmark_tes_signals.py`: comparador offline legacy vs simple
- `tests/`: pruebas del detector, benchmark y compatibilidad del servidor
- `manual/`: scripts manuales de inspeccion
- `reports/benchmarks/`: reportes JSON historicos
- `reports/plots/`: graficas agregadas
- `reports/plots_all/`: graficas por archivo
- `reports/plots_test/`: graficas puntuales de prueba

## Comandos

Desde la raiz del repo:

```powershell
python -m unittest discover -s postprocesamiento\evaluation\tests -v
```

```powershell
python postprocesamiento\evaluation\benchmark_tes_signals.py --dataset-dir tes_signals --preset auto --iou-threshold 0.30 --beta 2.0 --json-out postprocesamiento\evaluation\reports\benchmarks\benchmark_auto_manual.json
```

Scripts manuales:

```powershell
python postprocesamiento\evaluation\manual\step1_test_payload.py --json tu_archivo.json
python postprocesamiento\evaluation\manual\step2_test_router.py --json tu_archivo.json --cumplimiento 0
```

## Regla de uso

Nada de esta carpeta debe ser necesario para correr el servidor en plataforma.
Sirve para desarrollar, validar y comparar cambios de la logica interna.
