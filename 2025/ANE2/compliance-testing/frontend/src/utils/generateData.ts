export function generateSpectrumData(
  startFreq: number,
  endFreq: number,
  points: number = 1000
): { frequency: number; power: number }[] {
  const data: { frequency: number; power: number }[] = [];
  const freqStep = (endFreq - startFreq) / points;

  for (let i = 0; i < points; i++) {
    const freq = startFreq + i * freqStep;
    let power = -50 + Math.random() * 10;

    if (freq >= 95e6 && freq <= 96e6) {
      power = -35 + Math.sin((freq - 95.5e6) * 100) * 5;
    }
    if (freq >= 100e6 && freq <= 101e6) {
      power = -38 + Math.sin((freq - 100.5e6) * 80) * 4;
    }
    if (freq >= 92e6 && freq <= 93e6) {
      power = -40 + Math.sin((freq - 92.5e6) * 120) * 3;
    }

    data.push({ frequency: freq, power });
  }

  return data;
}

export function addNoiseToData(
  data: { frequency: number; power: number }[]
): { frequency: number; power: number }[] {
  return data.map(point => ({
    frequency: point.frequency,
    power: point.power + (Math.random() - 0.5) * 2,
  }));
}

/**
 * Simula datos de reporte TDT con métricas MER/BER y violaciones
 * Genera un escenario complejo con:
 * - Emisiones correctas
 * - Emisiones con violaciones de frecuencia y potencia
 * - Emisiones con MER/BER degradados
 */
export function generateSimulatedTDTReport(campaignId: number, campaignName: string) {
  const now = new Date();
  
  // Estructura base del reporte
  return {
    reporte_automatico: true,
    fecha_medicion: now.toISOString(),
    ubicacion: {
      estacion: "Estación de Monitoreo Norte",
      departamento: "BOGOTA D.C.",
      municipio: "BOGOTA D.C.",
      codigo_dane: "11001",
      coordenadas: {
        latitud: 4.7110,
        longitud: -74.0721
      }
    },
    campana: {
      id: campaignId,
      nombre: campaignName,
      estado: "completed",
      fecha_inicio: new Date(now.getTime() - 3600000).toISOString(), // Hace 1 hora
      fecha_fin: now.toISOString(),
      rango_frecuencias: {
        inicio_mhz: 470,
        fin_mhz: 698,
        ancho_banda_mhz: 228,
        resolucion_khz: 30
      }
    },
    analisis_espectral: {
      modo: "RMTDT",
      cumplimiento_general: false,
      emisiones_detectadas: 5,
      umbral_db: -70,
      correccion_aplicada: true
    },
    estadisticas: {
      total_mediciones: 1,
      total_emisiones: 5,
      autorizadas: 4,
      no_autorizadas: 1, // Fuera de parámetros
      emisiones_sin_licencia: 1, // Sin licencia
      porcentaje_cumplimiento: "60.0",
      frecuencias_unicas_autorizadas: 4,
      mediciones_analizadas: 1
    },
    mediciones: [
      {
        timestamp: now.getTime(),
        fecha_hora: now.toISOString(),
        num_emisiones: 5,
        emisiones_autorizadas: 3, // Cumplen
        emisiones_sin_licencia: 1,
        porcentaje_cumplimiento: "60.0",
        emisiones: [
          // 1. Emisión TDT Correcta (Canal 14)
          {
            frecuencia_mhz: 473.143, // Nominal 473.143 MHz
            dane_asociado: "11001",
            potencia_dbm: -35.2,
            ancho_banda_khz: 5800.0,
            estado_cumplimiento: "CUMPLE",
            cumple_fc: "SI",
            cumple_bw: "SI",
            fc_nominal_mhz: 473.143,
            delta_f_mhz: 0.000,
            bw_nominal_khz: 6000.0,
            delta_bw_khz: -200.0,
            p_nominal_dbm: -30.0,
            delta_p_db: -5.2,
            mer_db: 32.5, // MER Excelente
            ber_est: 1.2e-8 // BER Excelente
          },
          // 2. Emisión TDT Correcta (Canal 16)
          {
            frecuencia_mhz: 485.143,
            dane_asociado: "11001",
            potencia_dbm: -38.5,
            ancho_banda_khz: 5900.0,
            estado_cumplimiento: "CUMPLE",
            cumple_fc: "SI",
            cumple_bw: "SI",
            fc_nominal_mhz: 485.143,
            delta_f_mhz: 0.000,
            bw_nominal_khz: 6000.0,
            delta_bw_khz: -100.0,
            p_nominal_dbm: -30.0,
            delta_p_db: -8.5,
            mer_db: 28.4, // MER Bueno
            ber_est: 4.5e-7
          },
          // 3. Emisión TDT con Violación de Potencia y MER degradado (Canal 20)
          {
            frecuencia_mhz: 509.143,
            dane_asociado: "11001",
            potencia_dbm: -22.1, // Excede potencia nominal (-30) significativamente
            ancho_banda_khz: 6150.0, // Excede BW
            estado_cumplimiento: "FUERA_PARAMETROS",
            cumple_fc: "SI",
            cumple_bw: "NO", // Falla BW
            fc_nominal_mhz: 509.143,
            delta_f_mhz: 0.000,
            bw_nominal_khz: 6000.0,
            delta_bw_khz: 150.0, // +150 kHz (Violación BW)
            p_nominal_dbm: -30.0,
            delta_p_db: 7.9, // +7.9 dB (Violación Potencia)
            mer_db: 18.2, // MER Pobre (límite cliff effect)
            ber_est: 2.1e-3 // BER Alto
          },
          // 4. Emisión TDT con Desviación de Frecuencia (Canal 24)
          {
            frecuencia_mhz: 533.250, // Nominal 533.143 (+107 kHz offset)
            dane_asociado: "11001",
            potencia_dbm: -40.2,
            ancho_banda_khz: 5850.0,
            estado_cumplimiento: "FUERA_PARAMETROS",
            cumple_fc: "NO", // Falla FC
            cumple_bw: "SI",
            fc_nominal_mhz: 533.143,
            delta_f_mhz: 0.107, // Desviación significativa
            bw_nominal_khz: 6000.0,
            delta_bw_khz: -150.0,
            p_nominal_dbm: -30.0,
            delta_p_db: -10.2,
            mer_db: 22.1,
            ber_est: 1.5e-5
          },
          // 5. Emisión Pirata / Interferencia (Sin Licencia)
          {
            frecuencia_mhz: 550.000,
            potencia_dbm: -45.0,
            ancho_banda_khz: 200.0, // Señal angosta (tipo FM o PMR)
            estado_cumplimiento: "SIN_LICENCIA",
            cumple_fc: "N/A",
            cumple_bw: "N/A",
            detalles: {
              nota: "Señal no identificada en banda TDT"
            }
          }
        ]
      }
    ]
  };
}
