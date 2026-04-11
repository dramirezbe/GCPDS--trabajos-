import argparse
import os
from typing import Dict, List, Optional, cast

import matplotlib.pyplot as plt
import pandas as pd


VARIABLE_META: Dict[str, Dict[str, str]] = {
    "cpu_percent": {"label": "CPU Utilization", "unit": "%", "desc": "Total CPU usage percentage"},
    "arm_temp": {"label": "ARM Temperature", "unit": "C", "desc": "CPU/SoC temperature"},
    "arm_mhz": {"label": "ARM Clock", "unit": "MHz", "desc": "ARM core clock frequency"},
    "core_mhz": {"label": "Core Clock", "unit": "MHz", "desc": "Core frequency"},
    "h264_mhz": {"label": "H264 Clock", "unit": "MHz", "desc": "H264 block frequency"},
    "isp_mhz": {"label": "ISP Clock", "unit": "MHz", "desc": "Image Signal Processor frequency"},
    "v3d_mhz": {"label": "V3D Clock", "unit": "MHz", "desc": "3D engine frequency"},
    "uart_mhz": {"label": "UART Clock", "unit": "MHz", "desc": "UART clock frequency"},
    "pwm_mhz": {"label": "PWM Clock", "unit": "MHz", "desc": "PWM block frequency"},
    "emmc_mhz": {"label": "eMMC Clock", "unit": "MHz", "desc": "eMMC interface frequency"},
    "pixel_mhz": {"label": "Pixel Clock", "unit": "MHz", "desc": "Pixel clock"},
    "vec_mhz": {"label": "VEC Clock", "unit": "MHz", "desc": "VEC block frequency"},
    "hdmi_mhz": {"label": "HDMI Clock", "unit": "MHz", "desc": "HDMI subsystem frequency"},
    "dpi_mhz": {"label": "DPI Clock", "unit": "MHz", "desc": "Display Parallel Interface frequency"},
    "core_volt": {"label": "Core Voltage", "unit": "V", "desc": "Core voltage reported by firmware"},
    "sdram_c_volt": {"label": "SDRAM C Voltage", "unit": "V", "desc": "SDRAM controller voltage"},
    "sdram_i_volt": {"label": "SDRAM I Voltage", "unit": "V", "desc": "SDRAM IO voltage"},
    "sdram_p_volt": {"label": "SDRAM P Voltage", "unit": "V", "desc": "SDRAM PHY voltage"},
    "UV": {"label": "Undervoltage Flag", "unit": "bool", "desc": "Current undervoltage state"},
    "UV_occured": {"label": "Undervoltage Occurred", "unit": "bool", "desc": "Undervoltage occurred since boot"},
    "ArmFreqCap": {"label": "ARM Freq Capped", "unit": "bool", "desc": "Current ARM frequency cap state"},
    "ArmFreqCap_occured": {"label": "ARM Freq Cap Occurred", "unit": "bool", "desc": "ARM frequency cap occurred since boot"},
    "CurThrottle": {"label": "Current Throttle", "unit": "bool", "desc": "Current throttling state"},
    "Throttle_occured": {"label": "Throttle Occurred", "unit": "bool", "desc": "Throttle occurred since boot"},
    "SoftTempLimit": {"label": "Soft Temp Limit", "unit": "bool", "desc": "Current soft temperature limit state"},
    "SoftTempLimit_occured": {"label": "Soft Temp Limit Occurred", "unit": "bool", "desc": "Soft temperature limit occurred since boot"},
}


ABSOLUTE_UNDERVOLTAGE_THRESHOLDS_V: Dict[str, float] = {
    "EXT5V_V": 4.6,
    "HDMI_V": 4.6,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisis profundo de telemetria para detectar undervoltage."
    )
    parser.add_argument("-r", required=True, help="Ruta del CSV de telemetria de prueba/estres")
    parser.add_argument(
        "--idle",
        required=True,
        help="Ruta del CSV de telemetria en estado IDLE para calcular la linea base (threshold)",
    )
    parser.add_argument(
        "--output",
        default="output_plots",
        help="Directorio de salida para reportes y graficas",
    )
    parser.add_argument(
        "--drop-pct",
        type=float,
        default=3.0,
        help="Porcentaje de caida respecto a la linea base de IDLE para marcar undervoltage",
    )
    parser.add_argument(
        "--critical-drop-pct",
        type=float,
        default=6.0,
        help="Porcentaje de caida para clasificar evento critico",
    )
    return parser.parse_args()


def normalize_boolean_series(series: pd.Series) -> pd.Series:
    mapping = {
        "yes": True,
        "no": False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(mapping)
        .fillna(False)
        .astype(bool)
    )


def infer_label(col: str) -> str:
    if col in VARIABLE_META:
        return VARIABLE_META[col]["label"]

    if col.endswith("_V"):
        return f"{col[:-2].replace('_', ' ')} Voltage".title()
    if col.endswith("_A"):
        return f"{col[:-2].replace('_', ' ')} Current".title()
    if col.endswith("_mhz"):
        return f"{col[:-4].replace('_', ' ')} Clock".title()

    return col.replace("_", " ").title()


def infer_unit(col: str) -> str:
    if col in VARIABLE_META:
        return VARIABLE_META[col]["unit"]

    if col.endswith("_V") or col.endswith("_volt"):
        return "V"
    if col.endswith("_A"):
        return "A"
    if col.endswith("_mhz"):
        return "MHz"
    if col.endswith("_percent"):
        return "%"
    if "temp" in col.lower():
        return "C"
    return ""


def infer_description(col: str) -> str:
    if col in VARIABLE_META:
        return VARIABLE_META[col]["desc"]
    if col.endswith("_V"):
        return "Measured power rail voltage"
    if col.endswith("_A"):
        return "Measured rail current draw"
    if col.endswith("_mhz"):
        return "Measured block clock frequency"
    return "Telemetry variable"


def axis_label(col: str) -> str:
    label = infer_label(col)
    unit = infer_unit(col)
    if unit:
        return f"{label} [{unit}]"
    return label


def get_undervoltage_threshold(col: str, baseline: float, drop_pct: float) -> float:
    if col in ABSOLUTE_UNDERVOLTAGE_THRESHOLDS_V:
        return ABSOLUTE_UNDERVOLTAGE_THRESHOLDS_V[col]
    return baseline * (1 - (drop_pct / 100.0))


def find_event_groups(mask: pd.Series) -> pd.Series:
    return mask.ne(mask.shift(fill_value=False)).cumsum()


def classify_severity(drop_pct: float, duration_s: float, critical_drop_pct: float) -> str:
    if drop_pct >= critical_drop_pct or duration_s >= 30:
        return "critical"
    if drop_pct >= (critical_drop_pct * 0.6) or duration_s >= 10:
        return "warning"
    return "info"


def get_sample_period_seconds(index: pd.Index) -> Optional[float]:
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return None
    deltas = index.to_series().diff().dt.total_seconds().dropna()
    if deltas.empty:
        return None
    return float(deltas.median())


def build_event_table(
    df: pd.DataFrame,
    voltage_cols: List[str],
    baseline_map: Dict[str, float],
    drop_pct: float,
    critical_drop_pct: float,
    sample_period_s: Optional[float],
) -> pd.DataFrame:
    context_cols = [c for c in ["cpu_percent", "arm_temp", "VDD_CORE_A"] if c in df.columns]
    rows = []

    for col in voltage_cols:
        baseline = baseline_map[col]
        threshold = get_undervoltage_threshold(col, baseline, drop_pct)
        mask = df[col] < threshold
        if not mask.any():
            continue

        groups = find_event_groups(mask)
        for group_id, chunk in df[mask].groupby(groups[mask]):
            _ = group_id
            start = chunk.index.min()
            end = chunk.index.max()
            n_samples = int(len(chunk))

            if isinstance(df.index, pd.DatetimeIndex):
                duration_s = float((end - start).total_seconds())
                if sample_period_s is not None:
                    duration_s += sample_period_s
            else:
                duration_s = float(n_samples)

            min_v = float(chunk[col].min())
            avg_v = float(chunk[col].mean())
            observed_drop_pct = ((baseline - min_v) / baseline) * 100.0

            row = {
                "rail": col,
                "start": start,
                "end": end,
                "samples": n_samples,
                "duration_s": round(duration_s, 3),
                "baseline_v": round(baseline, 6),
                "threshold_v": round(threshold, 6),
                "min_v": round(min_v, 6),
                "avg_v": round(avg_v, 6),
                "drop_pct": round(observed_drop_pct, 3),
                "severity": classify_severity(observed_drop_pct, duration_s, critical_drop_pct),
            }
            for context_col in context_cols:
                row[f"avg_{context_col}"] = round(float(chunk[context_col].mean()), 4)

            rows.append(row)

    events = pd.DataFrame(rows)
    if events.empty:
        return events

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    events["_order"] = events["severity"].map(severity_order)
    events = events.sort_values(by=["_order", "drop_pct", "duration_s"], ascending=[True, False, False])
    events = events.drop(columns=["_order"]).reset_index(drop=True)
    return events


def plot_voltage_with_threshold(df: pd.DataFrame, col: str, baseline: float, threshold: float, output_dir: str) -> None:
    under = df[col] < threshold
    rail_label = infer_label(col)
    y_label = axis_label(col)
    plt.figure(figsize=(12, 4.5))
    plt.plot(df.index, df[col], label=rail_label, linewidth=1.1)
    
    # Etiquetas actualizadas para mostrar que proviene de IDLE
    plt.axhline(baseline, linestyle="--", linewidth=1.0, color="green", label=f"IDLE Baseline = {baseline:.4f} V")
    plt.axhline(threshold, linestyle=":", linewidth=1.2, color="red", label=f"Undervoltage threshold = {threshold:.4f} V")
    
    if under.any():
        plt.scatter(df.index[under], df.loc[under, col], s=10, label="Undervoltage sample", zorder=3, color="red")
        
    plt.title(f"{rail_label} - Undervoltage Detection (IDLE Referenced)")
    plt.xlabel("Timestamp")
    plt.ylabel(y_label)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{col}_undervoltage.png"), dpi=140)
    plt.close()


def preprocess_dataframe(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = [c.strip() for c in df.columns]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()

    for col in df.columns:
        if df[col].dtype == object:
            converted = cast(pd.Series, pd.to_numeric(df[col], errors="coerce"))
            if converted.notna().any():
                df[col] = converted
                
    return df


def main() -> None:
    args = parse_args()

    output_root = args.output
    plots_dir = os.path.join(output_root, "plots")
    reports_dir = os.path.join(output_root, "reports")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    # 1. Cargar el DataFrame principal de prueba
    df = preprocess_dataframe(args.r)
    
    # 2. Cargar el DataFrame de IDLE
    print(f"Cargando archivo IDLE como linea base: {args.idle}")
    df_idle = preprocess_dataframe(args.idle)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        raise ValueError("No se encontraron columnas numericas para analizar en el CSV de prueba.")

    sample_period_s = get_sample_period_seconds(df.index)

    voltage_cols = [c for c in numeric_cols if c.endswith("_V")]
    current_cols = [c for c in numeric_cols if c.endswith("_A")]
    flag_cols = [
        c
        for c in [
            "UV", "ArmFreqCap", "CurThrottle", "SoftTempLimit", 
            "UV_occured", "ArmFreqCap_occured", "Throttle_occured", "SoftTempLimit_occured"
        ]
        if c in df.columns
    ]

    # 3. Construir el baseline_map usando la mediana del archivo IDLE.csv
    baseline_map = {}
    for col in voltage_cols:
        if col in df_idle.columns:
            # Si el riel existe en IDLE, usamos su mediana como linea base
            baseline_map[col] = float(df_idle[col].median())
        else:
            # Fallback en caso de que el IDLE no tenga ese riel de voltaje
            print(f"Advertencia: El riel {col} no esta en {args.idle}. Usando la mediana de la prueba.")
            baseline_map[col] = float(df[col].median())

    # Estadisticas generales del CSV de prueba
    summary = df[numeric_cols].describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]).T
    summary.to_csv(os.path.join(reports_dir, "numeric_summary.csv"))

    # Salud de rails de voltaje
    rail_rows = []
    for col in voltage_cols:
        baseline = baseline_map[col]
        threshold = get_undervoltage_threshold(col, baseline, args.drop_pct)
        under_mask = df[col] < threshold
        rail_rows.append(
            {
                "rail": col,
                "idle_baseline_v": round(baseline, 6),
                "threshold_v": round(threshold, 6),
                "min_v": round(float(df[col].min()), 6),
                "mean_v": round(float(df[col].mean()), 6),
                "std_v": round(float(df[col].std()), 6),
                "p1_v": round(float(df[col].quantile(0.01)), 6),
                "p99_v": round(float(df[col].quantile(0.99)), 6),
                "undervoltage_samples": int(under_mask.sum()),
                "undervoltage_ratio_pct": round(float(under_mask.mean() * 100.0), 3),
            }
        )

    rail_health = pd.DataFrame(rail_rows).sort_values(by="undervoltage_ratio_pct", ascending=False)
    rail_health.to_csv(os.path.join(reports_dir, "voltage_rail_health.csv"), index=False)

    # Eventos de undervoltage
    events = build_event_table(
        df=df,
        voltage_cols=voltage_cols,
        baseline_map=baseline_map,
        drop_pct=args.drop_pct,
        critical_drop_pct=args.critical_drop_pct,
        sample_period_s=sample_period_s,
    )
    events_path = os.path.join(reports_dir, "undervoltage_events.csv")
    events.to_csv(events_path, index=False)

    # Conteo de flags de throttle/UV reportados por firmware
    if flag_cols:
        flag_rows = []
        for col in flag_cols:
            as_bool = normalize_boolean_series(df[col])
            flag_rows.append(
                {
                    "flag": col,
                    "active_samples": int(as_bool.sum()),
                    "active_ratio_pct": round(float(as_bool.mean() * 100.0), 3),
                }
            )
        pd.DataFrame(flag_rows).sort_values(by="active_ratio_pct", ascending=False).to_csv(
            os.path.join(reports_dir, "firmware_flags_summary.csv"), index=False
        )

    # Correlaciones para contexto causal
    corr_candidates = voltage_cols + [c for c in ["cpu_percent", "arm_temp"] if c in numeric_cols]
    corr_candidates += [c for c in current_cols if c in ["VDD_CORE_A", "3V3_SYS_A", "1V8_SYS_A"]]
    corr_candidates = list(dict.fromkeys(corr_candidates))

    if len(corr_candidates) >= 2:
        corr_source = pd.DataFrame(df[corr_candidates]).apply(
            lambda s: pd.to_numeric(s, errors="coerce")
        )
        corr = cast(pd.DataFrame, corr_source).corr()
        corr.to_csv(os.path.join(reports_dir, "correlation_matrix.csv"))
        corr_labels = [axis_label(c) for c in corr.columns]

        plt.figure(figsize=(0.9 * len(corr_candidates) + 2, 0.8 * len(corr_candidates) + 2))
        plt.imshow(corr, interpolation="nearest", aspect="auto")
        plt.colorbar(label="pearson r")
        plt.xticks(range(len(corr.columns)), corr_labels, rotation=90)
        plt.yticks(range(len(corr.index)), corr_labels)
        plt.title("Correlation Matrix: Voltage, Load, Temperature and Current")
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "correlation_matrix.png"), dpi=140)
        plt.close()

    glossary_rows = []
    for col in df.columns:
        glossary_rows.append(
            {
                "variable": col,
                "label": infer_label(col),
                "unit": infer_unit(col),
                "description": infer_description(col),
            }
        )
    pd.DataFrame(glossary_rows).to_csv(
        os.path.join(reports_dir, "variable_glossary.csv"), index=False
    )

    # Graficas por rail con umbral de undervoltage basado en IDLE
    for col in voltage_cols:
        baseline = baseline_map[col]
        threshold = get_undervoltage_threshold(col, baseline, args.drop_pct)
        plot_voltage_with_threshold(df, col, baseline, threshold, plots_dir)

    # Top eventos para revision rapida
    report_txt = os.path.join(reports_dir, "analysis_report.txt")
    with open(report_txt, "w", encoding="utf-8") as fp:
        fp.write("Telemetry Undervoltage Analysis (IDLE Referenced)\n")
        fp.write("=" * 48 + "\n\n")
        fp.write(f"Input CSV (Test): {args.r}\n")
        fp.write(f"Input CSV (IDLE Baseline): {args.idle}\n")
        fp.write(f"Rows analyzed: {len(df)}\n")
        fp.write(f"Voltage rails analyzed: {len(voltage_cols)}\n")
        if sample_period_s is not None:
            fp.write(f"Estimated sample period: {sample_period_s:.3f} s\n")
        fp.write(f"Undervoltage threshold drop: {args.drop_pct:.2f}%\n")
        fp.write(f"Critical drop threshold: {args.critical_drop_pct:.2f}%\n\n")

        if rail_health.empty:
            fp.write("No voltage rails found (*_V columns).\n")
        else:
            fp.write("Top rails by undervoltage ratio:\n")
            for _, row in rail_health.head(8).iterrows():
                fp.write(
                    f"- {row['rail']}: {row['undervoltage_ratio_pct']:.3f}% samples below threshold, "
                    f"min={row['min_v']:.4f}V idle_baseline={row['idle_baseline_v']:.4f}V\n"
                )

        fp.write("\n")
        if events.empty:
            fp.write("No undervoltage events detected with the configured IDLE threshold.\n")
        else:
            fp.write(f"Undervoltage events detected: {len(events)}\n")
            fp.write("Top 12 events by severity/drop:\n")
            for _, row in events.head(12).iterrows():
                fp.write(
                    f"- [{row['severity']}] {row['rail']} from {row['start']} to {row['end']} "
                    f"drop={row['drop_pct']:.2f}% min={row['min_v']:.4f}V duration={row['duration_s']:.2f}s\n"
                )

    print("Analisis completado exitosamente.")
    print(f"Reportes: {reports_dir}")
    print(f"Graficas: {plots_dir}")
    print(f"Eventos: {events_path}")


if __name__ == "__main__":
    main()