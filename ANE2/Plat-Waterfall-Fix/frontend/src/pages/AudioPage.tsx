import React from 'react';
import AudioPlayerComponent from '../components/AudioPlayerComponent';

/**
 * Página standalone para escuchar audio de un sensor específico
 * Acceso directo sin necesidad de medición activa
 * 
 * URL: /audio/{sensorId}
 * Ejemplo: http://rsm.ane.gov.co/audio/d0:65:78:9c:dd:d0
 */
const AudioPage: React.FC = () => {
  // Obtener sensorId de la URL
  const sensorId = window.location.pathname.split('/').pop() || 'unknown';
  
  return (
    <div className="min-h-screen bg-gray-100 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Monitoreo de Audio en Tiempo Real
          </h1>
          <p className="text-gray-600">
            Sistema ANE - Agencia Nacional del Espectro
          </p>
        </div>

        <AudioPlayerComponent
          sensorId={sensorId}
          wsUrl={`ws://${window.location.hostname}:3000`}
        />

        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Instrucciones para el Sensor
          </h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-700 mb-2">1. Conectar WebSocket</h3>
              <code className="block bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto">
                ws://{window.location.hostname}:3000/ws/audio/sensor/{sensorId}
              </code>
            </div>

            <div>
              <h3 className="font-medium text-gray-700 mb-2">2. Enviar Configuración (JSON)</h3>
              <code className="block bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto whitespace-pre">
{`{
  "codec": "opus",
  "sample_rate": 48000,
  "channels": 1,
  "frequency": 98500000,
  "modulation": "FM"
}`}
              </code>
            </div>

            <div>
              <h3 className="font-medium text-gray-700 mb-2">3. Enviar Frames Opus (Binario)</h3>
              <div className="bg-gray-50 p-3 rounded text-sm">
                <p className="mb-2 text-gray-700">Header (16 bytes, Big Endian):</p>
                <ul className="list-disc list-inside space-y-1 text-gray-600 ml-2">
                  <li><span className="font-mono">magic:</span> 0x4F505530 ('OPU0')</li>
                  <li><span className="font-mono">seq:</span> Número de secuencia</li>
                  <li><span className="font-mono">sample_rate:</span> 48000</li>
                  <li><span className="font-mono">channels:</span> 1</li>
                  <li><span className="font-mono">payload_len:</span> Tamaño del frame</li>
                </ul>
                <p className="mt-2 text-gray-700">Seguido por el frame Opus codificado</p>
              </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
              <p className="text-sm text-blue-700">
                <strong>Nota:</strong> El audio comenzará a reproducirse automáticamente 
                cuando el sensor comience a enviar frames. No se requiere configuración 
                previa ni medición activa.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <h3 className="font-medium text-yellow-800 mb-2">Estado del Servidor</h3>
          <p className="text-sm text-yellow-700 mb-2">
            Verificar estado del servidor de audio:
          </p>
          <code className="block bg-gray-800 text-green-400 p-2 rounded text-sm">
            curl http://{window.location.hostname}:3000/api/audio/status
          </code>
        </div>
      </div>
    </div>
  );
};

export default AudioPage;
