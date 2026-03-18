import { useEffect, useState } from 'react';
import { Radio, Plus, Trash2, X } from 'lucide-react';
import { antennaAPI, Antenna } from '../services/api';

export function AntennaManagement() {
  const [antennas, setAntennas] = useState<Antenna[]>([]);
  const [showAntennaForm, setShowAntennaForm] = useState(false);
  const [antennaFormData, setAntennaFormData] = useState<Partial<Antenna>>({
    name: '',
    type: 'Omnidireccional',
    frequency_min_hz: 0,
    frequency_max_hz: 0,
    gain_db: 0,
    description: '',
    inventory_code: ''
  });
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    loadAntennas();
  }, []);

  const loadAntennas = async () => {
    try {
      const data = await antennaAPI.getAll();
      setAntennas(data);
    } catch (error) {
      console.error('Error loading antennas:', error);
    }
  };

  const deleteAntenna = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar esta antena?')) return;
    try {
      await antennaAPI.delete(id);
      loadAntennas();
    } catch (error) {
      console.error('Error deleting antenna:', error);
    }
  };

  const validateForm = (): boolean => {
    const errors: { [key: string]: string } = {};
    
    // Validar nombre
    if (!antennaFormData.name || antennaFormData.name.trim() === '') {
      errors.name = 'El nombre de la antena es obligatorio';
    } else {
      // Validar duplicado de nombre
      const duplicate = antennas.find(a => a.name.toLowerCase() === antennaFormData.name?.toLowerCase());
      if (duplicate) {
        errors.name = 'Ya existe una antena con este nombre';
      }
    }

    // Validar código de inventario (Mandatorio)
    if (!antennaFormData.inventory_code || antennaFormData.inventory_code.trim() === '') {
      errors.inventory_code = 'El código de inventario es obligatorio';
    }
    
    // Validar tipo
    if (!antennaFormData.type) {
      errors.type = 'El tipo de antena es obligatorio';
    }
    
    // Validar frecuencia mínima
    const freqMinMHz = (antennaFormData.frequency_min_hz || 0) / 1e6;
    if (!antennaFormData.frequency_min_hz || freqMinMHz <= 0) {
      errors.frequency_min_hz = 'La frecuencia mínima debe ser mayor a 0';
    }
    
    // Validar frecuencia máxima
    const freqMaxMHz = (antennaFormData.frequency_max_hz || 0) / 1e6;
    if (!antennaFormData.frequency_max_hz || freqMaxMHz <= 0) {
      errors.frequency_max_hz = 'La frecuencia máxima debe ser mayor a 0';
    }
    
    // Validar que frecuencia mínima < frecuencia máxima
    if (freqMinMHz > 0 && freqMaxMHz > 0 && freqMinMHz >= freqMaxMHz) {
      errors.frequency_range = 'La frecuencia mínima debe ser menor que la frecuencia máxima';
    }
    
    // Validar ganancia
    if (antennaFormData.gain_db === undefined || antennaFormData.gain_db === null) {
      errors.gain_db = 'La ganancia es obligatoria';
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmitAntenna = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validar formulario
    if (!validateForm()) {
      return;
    }
    
    try {
      await antennaAPI.create(antennaFormData as Antenna);
      setShowAntennaForm(false);
      setAntennaFormData({
        name: '',
        type: 'Omnidireccional',
        frequency_min_hz: 0,
        frequency_max_hz: 0,
        gain_db: 0,
        description: '',
        inventory_code: ''
      });
      setValidationErrors({});
      loadAntennas();
      alert('Antena registrada exitosamente');
    } catch (error) {
      console.error('Error creating antenna:', error);
      alert('Error al registrar antena');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
            <Radio className="w-5 h-5 text-orange-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Antenas</h2>
        </div>
        <button
          onClick={() => setShowAntennaForm(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Agregar
        </button>
      </div>

      <p className="text-gray-600 mb-4">Gestiona las antenas del sistema.</p>

      {/* Lista de Antenas */}
      {antennas.length > 0 ? (
        <div className="space-y-3">
          {antennas.map((antenna) => (
            <div
              key={antenna.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-orange-300 hover:shadow-sm transition-all"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-800 text-lg mb-1">
                    {antenna.name}
                  </h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">Tipo:</span>
                      <span className="text-gray-700 font-medium">{antenna.type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">Rango de frecuencia:</span>
                      <span className="text-gray-700 font-medium">
                        {((antenna.frequency_min_hz || 0) / 1e6).toFixed(0)} - {((antenna.frequency_max_hz || 0) / 1e6).toFixed(0)} MHz
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">Ganancia:</span>
                      <span className="text-blue-600 font-semibold">{antenna.gain_db} dB</span>
                    </div>
                    {antenna.description && (
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-gray-500">Descripción:</span>
                        <span className="text-gray-600 text-xs">{antenna.description}</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => deleteAntenna(antenna.id!)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Eliminar antena"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Radio className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 mb-4">No hay antenas registradas</p>
          <button
            onClick={() => setShowAntennaForm(true)}
            className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
          >
            Registrar Primera Antena
          </button>
        </div>
      )}

      {/* Modal para registrar nueva antena */}
      {showAntennaForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[2000]">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">Registrar Antena</h3>
              <button
                onClick={() => setShowAntennaForm(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmitAntenna} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre de la antena *
                </label>
                <input
                  type="text"
                  required
                  value={antennaFormData.name}
                  onChange={(e) => {
                    setAntennaFormData({ ...antennaFormData, name: e.target.value });
                    if (validationErrors.name) {
                      setValidationErrors({ ...validationErrors, name: '' });
                    }
                  }}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                    validationErrors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Ej: Antena VHF/UHF"
                />
                {validationErrors.name && (
                  <p className="text-red-500 text-xs mt-1">{validationErrors.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Referencia del modelo *
                </label>
                <input
                  type="text"
                  required
                  value={antennaFormData.description}
                  onChange={(e) => setAntennaFormData({ ...antennaFormData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="Referencia del modelo del dispositivo o ficha técnica"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Código de inventario *
                </label>
                <input
                  type="text"
                  required
                  value={antennaFormData.inventory_code || ''}
                  onChange={(e) => {
                    setAntennaFormData({ ...antennaFormData, inventory_code: e.target.value });
                    if (validationErrors.inventory_code) {
                      setValidationErrors({ ...validationErrors, inventory_code: '' });
                    }
                  }}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                    validationErrors.inventory_code ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Código interno de inventario o patrimonial de la entidad"
                />
                {validationErrors.inventory_code && (
                  <p className="text-red-500 text-xs mt-1">{validationErrors.inventory_code}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo *
                </label>
                <select
                  required
                  value={antennaFormData.type}
                  onChange={(e) => setAntennaFormData({ ...antennaFormData, type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  <option value="Omnidireccional">Omnidireccional</option>
                  <option value="Direccional">Direccional</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Frecuencia mínima (MHz) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    required
                    min="0"
                    value={(antennaFormData.frequency_min_hz || 0) / 1e6}
                    onChange={(e) => {
                      setAntennaFormData({ ...antennaFormData, frequency_min_hz: parseFloat(e.target.value) * 1e6 });
                      if (validationErrors.frequency_min_hz || validationErrors.frequency_range) {
                        setValidationErrors({ 
                          ...validationErrors, 
                          frequency_min_hz: '', 
                          frequency_range: '' 
                        });
                      }
                    }}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                      validationErrors.frequency_min_hz || validationErrors.frequency_range ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="2"
                  />
                  {validationErrors.frequency_min_hz && (
                    <p className="text-red-500 text-xs mt-1">{validationErrors.frequency_min_hz}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Frecuencia máxima (MHz) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    required
                    min="0"
                    value={(antennaFormData.frequency_max_hz || 0) / 1e6}
                    onChange={(e) => {
                      setAntennaFormData({ ...antennaFormData, frequency_max_hz: parseFloat(e.target.value) * 1e6 });
                      if (validationErrors.frequency_max_hz || validationErrors.frequency_range) {
                        setValidationErrors({ 
                          ...validationErrors, 
                          frequency_max_hz: '', 
                          frequency_range: '' 
                        });
                      }
                    }}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                      validationErrors.frequency_max_hz || validationErrors.frequency_range ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="6000"
                  />
                  {validationErrors.frequency_max_hz && (
                    <p className="text-red-500 text-xs mt-1">{validationErrors.frequency_max_hz}</p>
                  )}
                </div>
              </div>
              
              {validationErrors.frequency_range && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-red-700 text-sm font-medium">{validationErrors.frequency_range}</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ganancia (dBi) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={antennaFormData.gain_db}
                  onChange={(e) => {
                    setAntennaFormData({ ...antennaFormData, gain_db: parseFloat(e.target.value) });
                    if (validationErrors.gain_db) {
                      setValidationErrors({ ...validationErrors, gain_db: '' });
                    }
                  }}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent ${
                    validationErrors.gain_db ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="1"
                />
                {validationErrors.gain_db && (
                  <p className="text-red-500 text-xs mt-1">{validationErrors.gain_db}</p>
                )}
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAntennaForm(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
