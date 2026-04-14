#example_extract_data_csv.py

from csv_dataclasses import TelemetryParser
import argparse
from pathlib import Path
import logging

def main():
    parser = argparse.ArgumentParser(
        description="Parsea y estructura telemetría de una Raspberry Pi 5 desde un archivo CSV."
    )
    parser.add_argument(
        "directory", 
        type=str, 
        help="Ruta a la carpeta que contiene el archivo ALL_PERIPH_MID_PETITION.csv"
    )
    
    args = parser.parse_args()
    folder_path = Path(args.directory)

    telemetry_parser = TelemetryParser()

    try:
        record_generator = telemetry_parser.read_directory(folder_path)
        
        logging.info("Imprimiendo la totalidad de variables para los primeros 3 registros:\n")
        
        for i, record in enumerate(record_generator):
            if i >= 3:
                break
            
            print(f"{'='*40}")
            print(f" REGISTRO #{i+1} | Timestamp: {record.timestamp}")
            print(f"{'='*40}")
            
            # --- 1. Variables Base ---
            print("\n[ BASE ]")
            print(f"{'cpu_percent':<20}: {record.cpu_percent} %")
            print(f"{'arm_temp':<20}: {record.arm_temp} °C")
            
            # --- 2. Relojes ---
            print("\n[ RELOJES (MHz) ]")
            for field, value in vars(record.clocks).items():
                print(f"{field:<20}: {value}")
                
            # --- 3. Voltajes ---
            print("\n[ VOLTAJES (V) ]")
            for field, value in vars(record.voltages).items():
                print(f"{field:<20}: {value}")
                
            # --- 4. Corrientes ---
            print("\n[ CORRIENTES (A) ]")
            for field, value in vars(record.currents).items():
                print(f"{field:<20}: {value}")
                
            # --- 5. Estado ---
            print("\n[ ESTADO Y THROTTLING ]")
            # Iteramos sobre el diccionario interno del estado excluyendo los registros readmr
            for field, value in vars(record.status).items():
                if field != "readmr_registers":
                    print(f"{field:<20}: {value}")
            
            print("\n[ REGISTROS READMR ]")
            for field, value in record.status.readmr_registers.items():
                print(f"{field:<20}: {value}")
                
            print("\n") # Espacio extra entre registros
            
    except FileNotFoundError:
        pass

if __name__ == "__main__":
    main()