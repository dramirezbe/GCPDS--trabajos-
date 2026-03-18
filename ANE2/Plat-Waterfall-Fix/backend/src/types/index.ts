export interface Sensor {
  id?: number;
  mac: string;
  name: string;
  description?: string;
  lat?: number;
  lng?: number;
  alt?: number;
  status?: 'active' | 'inactive' | 'online' | 'offline' | 'busy' | 'error' | 'delay';
  status_admin?: 'active' | 'inactive'; // Nuevo estado administrativo
  created_at?: number;
  updated_at?: number;
}

export interface Antenna {
  id?: number;
  name: string;
  type: string;
  frequency_min_hz?: number;
  frequency_max_hz?: number;
  gain_db?: number;
  description?: string;
  inventory_code?: string;
  created_at?: number;
  updated_at?: number;
}

export interface SensorAntenna {
  id?: number;
  sensor_id: number;
  antenna_id: number;
  port: number;
  is_active?: boolean;
  created_at?: number;
}

export interface SensorStatus {
  mac: string;
  metrics: {
    cpu: number[];
    ram_mb: number;
    swap_mb: number;
    disk_mb: number;
    temp_c: number;
  };
  total_metrics: {
    ram_mb: number;
    swap_mb: number;
    disk_mb: number;
  };
  delta_t_ms: number;
  ping_ms: number;
  timestamp_ms: number;
  last_kal_ms: number;
  last_ntp_ms: number;
  logs: string;
}

export interface SensorGPS {
  mac: string;
  lat: number;
  lng: number;
  alt?: number;
}

export interface SensorData {
  mac: string;
  campaign_id?: number;
  Pxx: number[];
  start_freq_hz: number;
  end_freq_hz: number;
  timestamp: number;
  lat?: number;
  lng?: number;
  excursion?: {
    unit: string;
    peak_to_peak_hz: number;
    peak_deviation_hz: number;
    rms_deviation_hz: number;
  };
  depth?: {
    unit: string;
    peak_to_peak: number;
    peak_deviation: number;
    rms_deviation: number;
  };
}

export interface SensorConfiguration {
  id?: number;
  mac: string;
  center_frequency: number;
  sample_rate_hz: number;
  span?: number; // Para retrocompatibilidad
  resolution_hz?: number;
  antenna_port?: number;
  window?: string;
  overlap?: number;
  lna_gain?: number;
  vga_gain?: number;
  antenna_amp?: boolean;
  // Nuevo formato simplificado
  demod_type?: string; // 'am' o 'fm'
  demodulation?: { // Formato antiguo para retrocompatibilidad
    type: string;
    bandwidth_hz: number;
    center_freq_hz: number;
    with_metrics: boolean;
    port_socket: string;
  };
  // Nuevo formato de filtro con start/end
  start_freq_hz?: number;
  end_freq_hz?: number;
  filter_start_freq_hz?: number;
  filter_end_freq_hz?: number;
  filter?: {
    start_freq_hz?: number;
    end_freq_hz?: number;
    // Formato antiguo (para retrocompatibilidad)
    type?: 'lowpass' | 'bandpass' | 'highpass';
    bw_hz?: number;
    order?: number;
  };
  is_active?: boolean;
  is_monitoring?: boolean;
  created_at?: number;
  updated_at?: number;
}

export interface Campaign {
  id?: number;
  name: string;
  description?: string;
  start_date?: number;
  end_date?: number;
  status?: 'active' | 'completed' | 'cancelled';
  created_at?: number;
  updated_at?: number;
}
