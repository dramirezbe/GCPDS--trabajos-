#!/usr/bin/env python3
"""Automate the ANE8 comparative telemetry analysis.

The script mirrors the notebook workflow and writes all artifacts into
results/<human_timestamp>/.
"""

from __future__ import annotations

import argparse
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


warnings.filterwarnings("ignore")
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (16, 10)


BASE_COLUMNS = [
    "Time_Human",
    "Time_Unix_ms",
    "Timestamp",
    "origen_dato",
    "config_ane8",
    "filename",
]

CORE_COLUMNS = ["Core_0_%", "Core_1_%", "Core_2_%", "Core_3_%"]
EXCLUDED_GLOBAL_COLUMNS = ["Swap_Used_%", "Throttled", *CORE_COLUMNS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ANE8 comparative telemetry analysis from the notebook logic."
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Project root. Defaults to the directory that contains this script.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=None,
        help="Directory where timestamped result folders will be created. Defaults to <base-path>/results.",
    )
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=300,
        help="Historical window to keep per configuration in seconds.",
    )
    return parser.parse_args()


def human_timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")


def build_results_dir(base_path: Path, results_root: Path | None) -> Path:
    root = results_root if results_root is not None else base_path / "results"
    output_dir = root / human_timestamp()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def find_source_files(db_path: Path) -> dict[str, dict[str, list[Path]]]:
    folders = {
        "NOservices": [
            db_path / "ane8-rpi(solo)-NOservices",
            db_path / "rpi(solo)-NOservices",
        ],
        "services": [
            db_path / "ane8-rpi(solo)-services",
            db_path / "rpi(solo)-services",
        ],
    }

    found: dict[str, dict[str, list[Path]]] = {}
    for config_name, candidate_paths in folders.items():
        config_files = {"HW_manual": [], "idle": []}
        for config_path in candidate_paths:
            if not config_path.exists():
                continue

            for csv_file in sorted(config_path.glob("*.csv")):
                name = csv_file.name
                if "HW_manual" in name:
                    config_files["HW_manual"].append(csv_file)
                elif "idle" in name:
                    config_files["idle"].append(csv_file)

        if not config_files["HW_manual"] and not config_files["idle"]:
            for config_path in candidate_paths:
                if not config_path.exists():
                    continue
                for csv_file in sorted(config_path.rglob("*.csv")):
                    name = csv_file.name
                    if "HW_manual" in name:
                        config_files["HW_manual"].append(csv_file)
                    elif "idle" in name:
                        config_files["idle"].append(csv_file)

        found[config_name] = config_files
    return found


def load_and_tag_csv(csv_path: Path, config_name: str, origin: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["origen_dato"] = origin
    df["config_ane8"] = config_name
    df["filename"] = csv_path.name
    return df


def load_configuration_data(files_by_config: dict[str, dict[str, list[Path]]]) -> dict[str, pd.DataFrame]:
    data_by_config: dict[str, pd.DataFrame] = {}

    for config_name, config_files in files_by_config.items():
        frames: list[pd.DataFrame] = []
        for origin in ("HW_manual", "idle"):
            for csv_path in config_files[origin]:
                try:
                    frame = load_and_tag_csv(csv_path, config_name, origin)
                    frames.append(frame)
                    print(f"Loaded {csv_path.name} -> {len(frame)} rows")
                except Exception as exc:  # pragma: no cover - runtime visibility is enough
                    print(f"Failed to load {csv_path.name}: {exc}")

        if frames:
            data_by_config[config_name] = pd.concat(frames, ignore_index=True, sort=False)
            print(f"Configuration {config_name}: {len(data_by_config[config_name])} rows")

    return data_by_config


def clean_and_type_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Time_Human" in df.columns:
        df["Time_Human"] = pd.to_datetime(df["Time_Human"], format="%H:%M:%S.%f", errors="coerce")

    if "Time_Unix_ms" in df.columns:
        df["Time_Unix_ms"] = pd.to_numeric(df["Time_Unix_ms"], errors="coerce")
        df["Timestamp"] = pd.to_datetime(df["Time_Unix_ms"], unit="ms", errors="coerce")

    object_columns = df.select_dtypes(include=["object"]).columns
    for column in object_columns:
        if column not in {"Time_Human", "origen_dato", "config_ane8", "filename", "Throttled"}:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "Timestamp" in df.columns:
        df = df.sort_values("Timestamp").reset_index(drop=True)
        df = df.drop_duplicates(subset=["Timestamp", "origen_dato"], keep="first")

    return df.reset_index(drop=True)


def clean_data_by_config(data_by_config: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    for config_name, df in data_by_config.items():
        cleaned[config_name] = clean_and_type_dataframe(df)
        null_counts = cleaned[config_name].isnull().sum()
        null_counts = null_counts[null_counts > 0]
        print(f"Cleaned {config_name}: {len(cleaned[config_name])} rows")
        if not null_counts.empty:
            print(null_counts.to_string())
    return cleaned


def filter_last_window(data_by_config: dict[str, pd.DataFrame], window_seconds: int) -> dict[str, pd.DataFrame]:
    filtered: dict[str, pd.DataFrame] = {}
    for config_name, df in data_by_config.items():
        if "Timestamp" not in df.columns or df.empty:
            continue

        t_min = df["Timestamp"].min()
        t_max = df["Timestamp"].max()
        duration = (t_max - t_min).total_seconds()
        if duration > window_seconds:
            start = t_max - pd.Timedelta(seconds=window_seconds)
            df_filtered = df[df["Timestamp"] >= start].copy()
        else:
            df_filtered = df.copy()

        filtered[config_name] = df_filtered.reset_index(drop=True)
        print(
            f"Window {config_name}: {len(df_filtered)} rows in "
            f"{(df_filtered['Timestamp'].max() - df_filtered['Timestamp'].min()).total_seconds():.1f} s"
        )

    return filtered


def add_relative_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Timestamp" not in df.columns:
        return df

    df["Tiempo_Relativo_s"] = np.nan
    for config_name in df["config_ane8"].dropna().unique():
        df_config = df[df["config_ane8"] == config_name]
        for origin in df_config["origen_dato"].dropna().unique():
            mask = (df["config_ane8"] == config_name) & (df["origen_dato"] == origin)
            subset = df.loc[mask].copy()
            if subset.empty:
                continue
            t_min = subset["Timestamp"].min()
            df.loc[mask, "Tiempo_Relativo_s"] = (subset["Timestamp"] - t_min).dt.total_seconds()
    return df


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def extract_series(df: pd.DataFrame, column: str) -> pd.Series:
    series = df.loc[:, column]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return pd.Series(series)


def available_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column not in BASE_COLUMNS]


def build_statistics(df_global: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    stats_rows: list[dict[str, object]] = []
    for config_name in ["NOservices", "services"]:
        df_config = df_global[df_global["config_ane8"] == config_name]
        for variable in variables:
            if variable not in df_config.columns:
                continue
            values = numeric_series(df_config[variable])
            if values.empty:
                continue
            stats_rows.append(
                {
                    "Config": config_name,
                    "Variable": variable,
                    "Min": float(values.min()),
                    "Max": float(values.max()),
                    "Mean": float(values.mean()),
                    "Std": float(values.std()),
                    "Samples": int(values.shape[0]),
                }
            )
    return pd.DataFrame(stats_rows)


def plot_global_analysis(df_global: pd.DataFrame, datos_hw: pd.DataFrame, datos_idle: pd.DataFrame) -> plt.Figure:
    hw_cols = [column for column in available_columns(datos_hw) if column not in EXCLUDED_GLOBAL_COLUMNS]
    idle_cols = [column for column in available_columns(datos_idle) if column not in EXCLUDED_GLOBAL_COLUMNS]

    variables = list(dict.fromkeys(hw_cols + idle_cols))
    
    # Excluir Tiempo_Relativo_s y temperaturas para manejarlas manualmente
    variables = [c for c in variables if c not in EXCLUDED_GLOBAL_COLUMNS and c not in ["Tiempo_Relativo_s", "Temp_HW_C", "Temp_C"]]

    num_plots = len(variables) + 3  # variables estándar + 1 gráfica combinada + 2 heatmaps
    num_cols = 3
    num_rows = (num_plots + num_cols - 1) // num_cols

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(18, 4 * num_rows))
    axes = np.array(axes).flatten()

    colors = {"NOservices": "blue", "services": "red"}

    # 1. Gráficas estándar
    idx = 0
    for variable in variables:
        ax = axes[idx]
        for config_name in ["NOservices", "services"]:
            df_config = df_global[df_global["config_ane8"] == config_name]
            if df_config.empty or variable not in df_config.columns:
                continue

            df_var = df_config[["Tiempo_Relativo_s", variable]].dropna()
            if len(df_var) > 1:
                x_norm = np.linspace(df_var["Tiempo_Relativo_s"].min(), df_var["Tiempo_Relativo_s"].max(), 100)
                y_norm = np.interp(x_norm, df_var["Tiempo_Relativo_s"], df_var[variable])
                ax.plot(x_norm, y_norm, linewidth=2, label=config_name, color=colors[config_name], alpha=0.8)

        ax.set_title(variable, fontsize=10, fontweight="bold")
        ax.set_xlabel("Tiempo relativo (s)", fontsize=8)
        ax.set_ylabel("Valor", fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        idx += 1

    # 2. Gráfica combinada de Temperaturas
    ax = axes[idx]
    for config_name in ["NOservices", "services"]:
        df_config = df_global[df_global["config_ane8"] == config_name]
        if df_config.empty: continue
        
        df_valid = df_config.dropna(subset=["Tiempo_Relativo_s"])
        if df_valid.empty: continue
        x_norm = np.linspace(df_valid["Tiempo_Relativo_s"].min(), df_valid["Tiempo_Relativo_s"].max(), 100)

        if "Temp_HW_C" in df_config.columns:
            df_var = df_config[["Tiempo_Relativo_s", "Temp_HW_C"]].dropna()
            if len(df_var) > 1:
                y_norm = np.interp(x_norm, df_var["Tiempo_Relativo_s"], df_var["Temp_HW_C"])
                ax.plot(x_norm, y_norm, linestyle="-", label=f"Thermic camera ({config_name})", color=colors[config_name])
        
        if "Temp_C" in df_config.columns:
            df_var = df_config[["Tiempo_Relativo_s", "Temp_C"]].dropna()
            if len(df_var) > 1:
                y_norm = np.interp(x_norm, df_var["Tiempo_Relativo_s"], df_var["Temp_C"])
                ax.plot(x_norm, y_norm, linestyle="--", label=f"CPU (SW) ({config_name})", color=colors[config_name])

    ax.set_title("Temperaturas (HW vs SW)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Tiempo relativo (s)", fontsize=8)
    ax.set_ylabel("Grados C", fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    idx += 1

    # 3. Heatmaps de CPU
    for hm_idx, config_name in enumerate(["NOservices", "services"]):
        ax = axes[idx + hm_idx]
        df_config = df_global[df_global["config_ane8"] == config_name]
        df_idle_config = df_config[df_config["origen_dato"] == "idle"].copy()

        df_valid = df_idle_config.dropna(subset=["Tiempo_Relativo_s"])
        if df_valid.empty:
            ax.set_visible(False)
            continue

        x_norm = np.linspace(df_valid["Tiempo_Relativo_s"].min(), df_valid["Tiempo_Relativo_s"].max(), 150)
        heatmap_data = []
        
        for core_col in CORE_COLUMNS:
            if core_col not in df_idle_config.columns: continue
            df_core = df_idle_config[["Tiempo_Relativo_s", core_col]].dropna()
            if len(df_core) > 1:
                y_norm = np.interp(x_norm, df_core["Tiempo_Relativo_s"], df_core[core_col])
                heatmap_data.append(y_norm)

        if not heatmap_data:
            ax.set_visible(False)
            continue

        image = ax.imshow(
            np.array(heatmap_data), cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=100,
            extent=[x_norm.min(), x_norm.max(), len(CORE_COLUMNS) - 0.5, -0.5]
        )
        ax.set_yticks(range(len(CORE_COLUMNS)))
        ax.set_yticklabels(CORE_COLUMNS, fontsize=9)
        ax.set_xlabel("Tiempo relativo (s)", fontsize=9)
        ax.set_title(f"Heatmap CPU - {config_name}", fontsize=10, fontweight="bold")
        plt.colorbar(image, ax=ax).set_label("Uso (%)", fontsize=8)

    # 4. Ocultar los espacios vacíos sobrantes en la cuadrícula
    for i in range(idx + 2, len(axes)):
        axes[i].set_visible(False)

    plt.tight_layout()
    plt.suptitle(
        "Analisis Comparativo ANE8 - Historico 5 minutos (Tiempo Relativo)\n"
        "HW_manual vs idle | NOservices vs services",
        fontsize=14,
        fontweight="bold",
        y=1.00,
    )
    plt.subplots_adjust(top=0.96)

    return fig


def main() -> None:
    args = parse_args()
    base_path = args.base_path.resolve()
    db_path = base_path / "db" / "ane7"
    output_dir = build_results_dir(base_path, args.results_root)

    print(f"Base path: {base_path}")
    print(f"Database path exists: {db_path.exists()}")
    print(f"Results dir: {output_dir}")

    files_by_config = find_source_files(db_path)
    for config_name, config_files in files_by_config.items():
        print(f"{config_name}: HW_manual={len(config_files['HW_manual'])}, idle={len(config_files['idle'])}")

    data_by_config = load_configuration_data(files_by_config)
    if not data_by_config:
        raise RuntimeError("No source CSV files were loaded.")

    cleaned_by_config = clean_data_by_config(data_by_config)
    filtered_by_config = filter_last_window(cleaned_by_config, args.window_seconds)

    df_global = pd.concat(filtered_by_config.values(), ignore_index=True)
    df_global = add_relative_time(df_global)

    datos_hw = df_global[df_global["origen_dato"] == "HW_manual"].copy()
    datos_idle = df_global[df_global["origen_dato"] == "idle"].copy()

    hw_cols = [column for column in available_columns(datos_hw) if column not in EXCLUDED_GLOBAL_COLUMNS]
    idle_cols = [column for column in available_columns(datos_idle) if column not in EXCLUDED_GLOBAL_COLUMNS]

    stats_variables = list(dict.fromkeys(hw_cols + idle_cols))
    stats_variables = [column for column in stats_variables if column not in EXCLUDED_GLOBAL_COLUMNS]
    df_stats = build_statistics(df_global, stats_variables)

    fig_global = plot_global_analysis(df_global, datos_hw, datos_idle)

    global_path = output_dir / "01_analisis_global_5min.png"

    fig_global.savefig(global_path, dpi=150, bbox_inches="tight")

    plt.close(fig_global)

    stats_path = output_dir / "10_estadisticas_resumidas.csv"
    df_stats.to_csv(stats_path, index=False)

    print(f"Saved: {global_path.name}")
    print(f"Saved: {stats_path.name}")
    print(f"All outputs are in: {output_dir}")


if __name__ == "__main__":
    main()