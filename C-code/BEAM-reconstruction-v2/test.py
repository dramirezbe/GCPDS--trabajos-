import pandas as pd

def consultar_modulacion(ciudad, canal):
    """
    Consulta la modulación para una ciudad y canal específicos
    
    Parámetros:
    ciudad (str): Nombre de la ciudad a consultar
    canal (int): Número del canal (14-51)
    
    Retorna:
    tuple: (modulacion, frecuencia_mhz)
    """
    try:
        # Leer el archivo CSV
        df = pd.read_csv('TDT_CHANNELS.csv')
        
        # Convertir el número de canal al formato "Canal XX"
        canal_str = f"Canal {canal}"
        
        # Verificar si el canal existe
        if canal_str not in df['Canal'].values:
            return None, None
            
        # Obtener la fila correspondiente al canal
        fila = df[df['Canal'] == canal_str].iloc[0]
        
        # Obtener la modulación para la ciudad específica
        modulacion = fila[ciudad]
        frecuencia = fila['Frecuencia Central (MHz)']
        
        return modulacion, frecuencia
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def obtener_info_modulacion(modulacion):
    """
    Proporciona información sobre el tipo de modulación
    """
    info = {
        '64-QAM': 'Modulación de Amplitud en Cuadratura de 64 estados. Permite transmitir 6 bits por símbolo.',
        '16-QAM': 'Modulación de Amplitud en Cuadratura de 16 estados. Permite transmitir 4 bits por símbolo.'
    }
    return info.get(modulacion, 'Modulación no reconocida')

# Ejemplo de uso
if __name__ == "__main__":
    # Solicitar entrada al usuario
    ciudad = input("Ingrese el nombre de la ciudad: ")
    canal = int(input("Ingrese el número del canal (14-51): "))
    
    # Realizar la consulta
    modulacion, frecuencia = consultar_modulacion(ciudad, canal)
    
    if modulacion and frecuencia:
        print(f"\nResultados para {ciudad}, Canal {canal}:")
        print(f"Modulación: {modulacion}")
        print(f"Frecuencia: {frecuencia} MHz")
        print(f"\nInformación de la modulación:")
        print(obtener_info_modulacion(modulacion))
    else:
        print("No se encontró información para los datos proporcionados.")