import axios from 'axios';

// Detectar si estamos en localhost o producción
// El navegador devuelve 'rsm.ane.gov.co' en producción y 'localhost' o '127.0.0.1' en desarrollo
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// En producción, usar SIEMPRE ruta relativa '/api' para evitar Mixed Content.
// El navegador usará automáticamente el protocolo actual (https) y el dominio actual.
const API_BASE_URL = isLocalhost 
  ? (import.meta.env.VITE_API_URL || 'http://localhost:3000/api') 
  : '/api';

console.log('🌐 API Config:', {
  hostname: window.location.hostname,
  protocol: window.location.protocol,
  isLocalhost,
  API_BASE_URL,
  envViteApi: import.meta.env.VITE_API_URL
});

// Configurar timeout global de axios para peticiones largas
axios.defaults.timeout = 3600000; // 1 hora

// Interceptor para agregar el token de autenticación
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Tipos
export interface Sensor {
  id?: number;
  mac: string;
  name: string;
  description?: string;
  lat?: number;
  lng?: number;
  alt?: number;
  status?: 'active' | 'inactive' | 'error' | 'online' | 'offline' | 'busy' | 'delay';
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
}

export interface SpectrumData {
  device_id: number;
  campaign_id: number;
  Pxx: number[];
  start_freq_hz: number;
  end_freq_hz: number;
  timestamp: number;
  excursion_hz?: number;
  depth?: number;
}

export interface SensorConfiguration {
  start_freq_hz: number;
  end_freq_hz: number;
  resolution_hz?: number;
  antenna_port?: number;
  window?: string;
  overlap?: number;
  sample_rate_hz?: number;
  lna_gain?: number;
  vga_gain?: number;
  antenna_amp?: boolean;
}

// API de Sensores
export const sensorAPI = {
  async getAll(): Promise<Sensor[]> {
    const response = await axios.get(`${API_BASE_URL}/sensors`);
    return response.data;
  },

  async validateStatus(): Promise<any> {
    const response = await axios.post(`${API_BASE_URL}/sensors/validate-status`);
    return response.data;
  },

  async getById(id: number): Promise<Sensor> {
    const response = await axios.get(`${API_BASE_URL}/sensors/${id}`);
    return response.data;
  },

  async getByMac(mac: string): Promise<Sensor> {
    const response = await axios.get(`${API_BASE_URL}/sensors/mac/${mac}`);
    return response.data;
  },

  async create(sensor: Sensor): Promise<Sensor> {
    const response = await axios.post(`${API_BASE_URL}/sensors`, sensor);
    return response.data;
  },

  async update(id: number, sensor: Partial<Sensor>): Promise<Sensor> {
    const response = await axios.put(`${API_BASE_URL}/sensors/${id}`, sensor);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/sensors/${id}`);
  },

  async getAntennas(sensorId: number): Promise<Antenna[]> {
    const response = await axios.get(`${API_BASE_URL}/sensors/${sensorId}/antennas`);
    return response.data;
  },

  async assignAntenna(sensorId: number, antennaId: number, port: number): Promise<any> {
    const response = await axios.post(`${API_BASE_URL}/sensors/${sensorId}/antennas`, { antenna_id: antennaId, port });
    return response.data;
  },

  async unassignAntenna(sensorId: number, antennaId: number): Promise<any> {
    const response = await axios.delete(`${API_BASE_URL}/sensors/${sensorId}/antennas/${antennaId}`);
    return response.data;
  },
};

export const antennaAPI = {
  async getAll(): Promise<Antenna[]> {
    const response = await axios.get(`${API_BASE_URL}/antennas`);
    return response.data;
  },

  async create(antenna: Antenna): Promise<Antenna> {
    const response = await axios.post(`${API_BASE_URL}/antennas`, antenna);
    return response.data;
  },

  async update(id: number, antenna: Partial<Antenna>): Promise<Antenna> {
    const response = await axios.put(`${API_BASE_URL}/antennas/${id}`, antenna);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/antennas/${id}`);
  },
};

export const sensorDataAPI = {
  async getLatestData(mac: string, limit: number = 100): Promise<SpectrumData[]> {
    const response = await axios.get(`${API_BASE_URL}/sensor/${mac}/latest-data`, { params: { limit } });
    return response.data;
  },

  async getDataByRange(mac: string, start: number, end: number): Promise<SpectrumData[]> {
    const response = await axios.get(`${API_BASE_URL}/sensor/${mac}/data/range`, { params: { start, end } });
    return response.data;
  },

  async sendConfiguration(mac: string, config: SensorConfiguration): Promise<any> {
    const response = await axios.post(`${API_BASE_URL}/sensor/${mac}/configuration`, config);
    return response.data;
  },

  async getConfiguration(mac: string): Promise<SensorConfiguration> {
    const response = await axios.get(`${API_BASE_URL}/sensor/${mac}/configuration`);
    return response.data;
  },

  async getLatestStatus(mac: string): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/sensor/${mac}/latest-status`);
    return response.data;
  },
  
  async getLatestGPS(mac: string): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/sensor/${mac}/latest-gps`);
    return response.data;
  },
};

export interface Statistics {
  total_storage_bytes: number;
  campaigns: {
    total: number;
    scheduled: number;
    running: number;
    completed: number;
    cancelled: number;
  };
  sensors: {
    total: number;
    active: number;
    inactive: number;
    error: number;
  };
}

export const statisticsAPI = {
  async getSummary(): Promise<Statistics> {
    const response = await axios.get(`${API_BASE_URL}/campaigns/statistics/summary`);
    return response.data;
  },
};

// API de Configuración
export const configAPI = {
  async get(): Promise<Record<string, string>> {
    const response = await axios.get(`${API_BASE_URL}/config`);
    return response.data;
  },

  async update(updates: Record<string, string | number>): Promise<any> {
    const response = await axios.post(`${API_BASE_URL}/config`, updates);
    return response.data;
  }
};

// API de Alertas
export const alertsAPI = {
  async getHistory(filters: { 
    start_date?: number, 
    end_date?: number, 
    sensor_mac?: string,
    limit?: number,
    offset?: number 
  }): Promise<{ alerts: any[], total: number }> {
    const response = await axios.get(`${API_BASE_URL}/alerts`, { params: filters });
    return response.data;
  }
};
