import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Radio, ChevronDown, ChevronUp, Filter, Plus, Eye, ChevronLeft, ChevronRight, XCircle, Trash2 } from 'lucide-react';
import { Sensor } from '../services/api';
import { CampaignModal } from './CampaignModal';
import { CampaignDataViewer } from './CampaignDataViewer';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface Campaign {
  id: number;
  name: string;
  status: 'scheduled' | 'running' | 'completed' | 'cancelled';
  devices: number;
  start_freq_mhz: number;
  end_freq_mhz: number;
  bandwidth_mhz: number;
  resolution_khz: number;
  start_date: string;
  end_date: string;
  start_time?: string;
  end_time?: string;
  interval_seconds: number;
  sensors: string[]; // MACs de sensores
  sensor_names?: string[]; // Nombres de sensores
  created_by_name?: string; // Nombre del usuario que creó la campaña
  gps_coordinates?: { mac: string; lat: number; lng: number }[]; // Coordenadas GPS al finalizar
}

interface CampaignsListProps {
  sensors: Sensor[];
  isAdmin: boolean;
  prefillData?: any;
}

export function CampaignsList({ sensors, isAdmin, prefillData }: CampaignsListProps) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [filteredCampaigns, setFilteredCampaigns] = useState<Campaign[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [nameFilter, setNameFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [applyFilters, setApplyFilters] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [selectedCampaignForViewer, setSelectedCampaignForViewer] = useState<{ campaign: Campaign; sensors: string[] } | null>(null);
  const [hideCampaignsList, setHideCampaignsList] = useState(false);
  
  // Abrir modal si hay datos pre-cargados
  useEffect(() => {
    if (prefillData) {
      setShowModal(true);
    }
  }, [prefillData]);

  // Estados de paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Cargar campañas
  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/campaigns`);
      const data = response.data;
      
      // Inyectar campaña simulada TDT para pruebas de reporte
      const simulatedCampaign: Campaign = {
        id: 99999,
        name: "Simulación Reporte TDT (MER/BER)",
        status: "completed",
        devices: 1,
        start_freq_mhz: 470,
        end_freq_mhz: 698,
        bandwidth_mhz: 228,
        resolution_khz: 30,
        start_date: new Date().toISOString(),
        end_date: new Date().toISOString(),
        interval_seconds: 60,
        sensors: ["SIM-SENSOR-01"],
        sensor_names: ["Simulador TDT"],
        created_by_name: "Sistema",
        gps_coordinates: [{ mac: "SIM-SENSOR-01", lat: 4.7110, lng: -74.0721 }]
      };
      
      const allCampaigns = Array.isArray(data) ? [simulatedCampaign, ...data] : [simulatedCampaign];
      
      setCampaigns(allCampaigns);
      setFilteredCampaigns(allCampaigns);
    } catch (error) {
      console.error('Error loading campaigns:', error);
      setCampaigns([]);
      setFilteredCampaigns([]);
    }
  };

  // Aplicar filtros
  useEffect(() => {
    if (!applyFilters) {
      setFilteredCampaigns(campaigns);
      setCurrentPage(1); // Resetear a página 1 cuando se quitan los filtros
      return;
    }

    let filtered = campaigns;

    if (nameFilter) {
      filtered = filtered.filter(c => 
        c.name.toLowerCase().includes(nameFilter.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(c => c.status === statusFilter);
    }

    setFilteredCampaigns(filtered);
    setCurrentPage(1); // Resetear a página 1 cuando cambian los filtros
  }, [campaigns, nameFilter, statusFilter, applyFilters]);

  // Calcular datos de paginación
  const totalPages = Math.ceil(filteredCampaigns.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentCampaigns = filteredCampaigns.slice(startIndex, endIndex);

  // Funciones de navegación
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const goToFirstPage = () => setCurrentPage(1);
  const goToLastPage = () => setCurrentPage(totalPages);
  const goToPreviousPage = () => goToPage(currentPage - 1);
  const goToNextPage = () => goToPage(currentPage + 1);

  // Generar números de página a mostrar
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      // Mostrar todas las páginas si son pocas
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Mostrar páginas con elipsis
      if (currentPage <= 3) {
        for (let i = 1; i <= 4; i++) pages.push(i);
        pages.push('...');
        pages.push(totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1);
        pages.push('...');
        for (let i = totalPages - 3; i <= totalPages; i++) pages.push(i);
      } else {
        pages.push(1);
        pages.push('...');
        pages.push(currentPage - 1);
        pages.push(currentPage);
        pages.push(currentPage + 1);
        pages.push('...');
        pages.push(totalPages);
      }
    }

    return pages;
  };

  const handleCancelCampaign = async (campaignId: number) => {
    if (!confirm('¿Está seguro que desea cancelar esta campaña?')) {
      return;
    }

    try {
      await axios.post(`${API_BASE_URL}/campaigns/${campaignId}/stop`);
      
      // Recargar la lista de campañas
      loadCampaigns();
      alert('Campaña cancelada exitosamente');
    } catch (error) {
      console.error('Error canceling campaign:', error);
      alert('Error al cancelar la campaña');
    }
  };

  const handleDeleteCampaign = async (campaignId: number) => {
    if (!confirm('¿Está seguro que desea eliminar esta campaña? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/campaigns/${campaignId}`);
      
      // Recargar la lista de campañas
      loadCampaigns();
      alert('Campaña eliminada exitosamente');
    } catch (error) {
      console.error('Error deleting campaign:', error);
      alert('Error al eliminar la campaña');
    }
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      scheduled: { label: 'Programada', class: 'bg-green-100 text-green-700' },
      running: { label: 'En ejecución', class: 'bg-blue-100 text-blue-700' },
      completed: { label: 'Terminada', class: 'bg-gray-100 text-gray-700' },
      cancelled: { label: 'Cancelada', class: 'bg-red-100 text-red-700' }
    };
    const badge = badges[status as keyof typeof badges] || { label: status, class: 'bg-gray-100 text-gray-700' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.class}`}>
        {badge.label}
      </span>
    );
  };

  // Contar campañas por estado
  const statusCounts = {
    scheduled: campaigns.filter(c => c.status === 'scheduled').length,
    running: campaigns.filter(c => c.status === 'running').length,
    completed: campaigns.filter(c => c.status === 'completed').length,
    cancelled: campaigns.filter(c => c.status === 'cancelled').length,
    total: campaigns.length
  };

  return (
    <div className="flex flex-1 overflow-hidden h-full">
      {/* Panel izquierdo - Lista de campañas */}
      {!hideCampaignsList && (
        <div className="w-96 bg-white border-r overflow-y-auto shadow-lg flex-shrink-0">
        {/* Header */}
        <div className="p-4 border-b bg-white sticky top-0 z-10">
          <h2 className="text-xl font-bold text-gray-800 mb-3">Campañas</h2>
          
          {/* Estadísticas */}
          <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
            <div>
              <span className="text-gray-600">Programadas:</span>
              <span className="ml-1 font-semibold text-green-600">{statusCounts.scheduled}</span>
            </div>
            <div>
              <span className="text-gray-600">En ejecución:</span>
              <span className="ml-1 font-semibold text-blue-600">{statusCounts.running}</span>
            </div>
            <div>
              <span className="text-gray-600">Finalizadas:</span>
              <span className="ml-1 font-semibold text-gray-600">{statusCounts.completed}</span>
            </div>
            <div>
              <span className="text-gray-600">Canceladas:</span>
              <span className="ml-1 font-semibold text-red-600">{statusCounts.cancelled}</span>
            </div>
          </div>
          <div className="text-sm mb-3">
            <span className="text-gray-600">Total:</span>
            <span className="ml-1 font-semibold text-orange-600">{statusCounts.total}</span>
          </div>

          {/* Toggle Filtros */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <div className="flex items-center gap-2">
              <Filter size={16} />
              <span className="text-sm font-medium">Filtros</span>
            </div>
            {showFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {/* Panel de filtros */}
          {showFilters && (
            <div className="mt-3 space-y-3 p-3 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Nombre</label>
                <input
                  type="text"
                  value={nameFilter}
                  onChange={(e) => setNameFilter(e.target.value)}
                  placeholder="Buscar por nombre..."
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-600 mb-1">Estado</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">-- Todos --</option>
                  <option value="scheduled">Programada</option>
                  <option value="running">En ejecución</option>
                  <option value="completed">Terminada</option>
                  <option value="cancelled">Cancelada</option>
                </select>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-gray-600">
                  {filteredCampaigns.length} resultado{filteredCampaigns.length !== 1 ? 's' : ''}
                </span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-sm text-gray-600">Aplicar filtros</span>
                  <input
                    type="checkbox"
                    checked={applyFilters}
                    onChange={(e) => setApplyFilters(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Lista de campañas */}
        <div className="divide-y">
          {currentCampaigns.map((campaign) => (
            <div key={campaign.id} className="p-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">#{campaign.id}</span>
                    <h3 className="font-semibold text-gray-800">{campaign.name}</h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(campaign.status)}
                  {campaign.status === 'completed' && campaign.sensors && campaign.sensors.length > 0 && (
                    <button
                      onClick={() => setSelectedCampaignForViewer({ campaign, sensors: campaign.sensors })}
                      className="p-2 hover:bg-blue-100 rounded-lg transition-colors group"
                      title="Ver datos de la campaña"
                    >
                      <Eye size={18} className="text-blue-500 group-hover:text-blue-600" />
                    </button>
                  )}
                  {isAdmin && (campaign.status === 'scheduled' || campaign.status === 'running') && (
                    <button
                      onClick={() => handleCancelCampaign(campaign.id)}
                      className="p-2 hover:bg-red-100 rounded-lg transition-colors group"
                      title="Cancelar campaña"
                    >
                      <XCircle size={18} className="text-red-500 group-hover:text-red-600" />
                    </button>
                  )}
                  {isAdmin && (
                    <button
                      onClick={() => handleDeleteCampaign(campaign.id)}
                      className="p-2 hover:bg-red-100 rounded-lg transition-colors group"
                      title="Eliminar campaña"
                    >
                      <Trash2 size={18} className="text-gray-500 group-hover:text-red-600" />
                    </button>
                  )}
                </div>
              </div>
              
              <div className="text-sm text-gray-600 mb-2">
                {campaign.devices} dispositivo{campaign.devices !== 1 ? 's' : ''}
                {campaign.sensor_names && campaign.sensor_names.length > 0 && (
                  <span className="text-xs text-gray-500 ml-1">
                    ({campaign.sensor_names.join(', ')})
                  </span>
                )}
              </div>

              <div className="space-y-1 text-xs text-gray-600">
                {campaign.created_by_name && (
                  <div className="flex justify-between">
                    <span>Creada por:</span>
                    <span className="font-medium">{campaign.created_by_name}</span>
                  </div>
                )}
                {campaign.status === 'completed' && campaign.gps_coordinates && campaign.gps_coordinates.length > 0 && (
                  <div className="mt-2 p-2 bg-gray-100 rounded">
                    <span className="block font-medium mb-1">Coordenadas GPS:</span>
                    {campaign.gps_coordinates.map((gps, idx) => (
                      <div key={idx} className="flex justify-between text-[10px]">
                        <span>{gps.mac}:</span>
                        <span>
                          {typeof gps.lat === 'number' ? gps.lat.toFixed(5) : 'N/A'}, 
                          {typeof gps.lng === 'number' ? gps.lng.toFixed(5) : 'N/A'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Frecuencia Inicial:</span>
                  <span className="font-medium">{campaign.start_freq_mhz} MHz</span>
                </div>
                <div className="flex justify-between">
                  <span>Frecuencia Final:</span>
                  <span className="font-medium">{campaign.end_freq_mhz} MHz</span>
                </div>
                <div className="flex justify-between">
                  <span>Ancho de Banda:</span>
                  <span className="font-medium">{campaign.bandwidth_mhz} MHz</span>
                </div>
                <div className="flex justify-between">
                  <span>Resolución:</span>
                  <span className="font-medium">{campaign.resolution_khz} kHz</span>
                </div>
                <div className="flex justify-between">
                  <span>Fecha Inicio:</span>
                  <span className="font-medium">{campaign.start_date.split('T')[0]}</span>
                </div>
                <div className="flex justify-between">
                  <span>Fecha Fin:</span>
                  <span className="font-medium">{campaign.end_date.split('T')[0]}</span>
                </div>
                <div className="flex justify-between">
                  <span>Hora Inicio:</span>
                  <span className="font-medium">{(campaign as any).start_time || 'No especificada'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Hora Fin:</span>
                  <span className="font-medium">{(campaign as any).end_time || 'No especificada'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Intervalo de Muestreo:</span>
                  <span className="font-medium">{campaign.interval_seconds} segundos</span>
                </div>
              </div>
            </div>
          ))}

          {filteredCampaigns.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <Radio className="mx-auto mb-2 opacity-50" size={48} />
              <p>No hay campañas que coincidan con los filtros</p>
            </div>
          )}
        </div>

        {/* Controles de paginación */}
        {filteredCampaigns.length > 0 && totalPages > 1 && (
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              {/* Información de página actual */}
              <div className="text-sm text-gray-600">
                Mostrando <span className="font-medium">{startIndex + 1}</span> - <span className="font-medium">{Math.min(endIndex, filteredCampaigns.length)}</span> de <span className="font-medium">{filteredCampaigns.length}</span> campañas
              </div>

              {/* Selector de items por página */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">Items por página:</label>
                <select
                  value={itemsPerPage}
                  onChange={(e) => {
                    setItemsPerPage(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>

            {/* Botones de navegación */}
            <div className="flex items-center justify-center gap-2">
              {/* Botón Primera Página */}
              <button
                onClick={goToFirstPage}
                disabled={currentPage === 1}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentPage === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                title="Primera página"
              >
                «
              </button>

              {/* Botón Anterior */}
              <button
                onClick={goToPreviousPage}
                disabled={currentPage === 1}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentPage === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                title="Página anterior"
              >
                ‹
              </button>

              {/* Números de página */}
              {getPageNumbers().map((page, index) => (
                typeof page === 'number' ? (
                  <button
                    key={index}
                    onClick={() => goToPage(page)}
                    className={`px-3 py-1 text-sm rounded-md transition-colors ${
                      currentPage === page
                        ? 'bg-blue-500 text-white font-medium'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {page}
                  </button>
                ) : (
                  <span key={index} className="px-2 text-gray-400">
                    {page}
                  </span>
                )
              ))}

              {/* Botón Siguiente */}
              <button
                onClick={goToNextPage}
                disabled={currentPage === totalPages}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentPage === totalPages
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                title="Página siguiente"
              >
                ›
              </button>

              {/* Botón Última Página */}
              <button
                onClick={goToLastPage}
                disabled={currentPage === totalPages}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentPage === totalPages
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                title="Última página"
              >
                »
              </button>
            </div>

            {/* Página actual */}
            <div className="text-center mt-2 text-xs text-gray-500">
              Página {currentPage} de {totalPages}
            </div>
          </div>
        )}

        {/* Botón para programar campaña en el panel */}
        <div className="p-4 border-t bg-white sticky bottom-0">
          <button
            onClick={() => setShowModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg shadow-lg transition-colors"
          >
            <Plus size={20} />
            <span className="font-medium">Programar campaña</span>
          </button>
        </div>
        </div>
      )}

      {/* Botón para ocultar/mostrar panel de campañas */}
      {selectedCampaignForViewer && (
        <button
          onClick={() => setHideCampaignsList(!hideCampaignsList)}
          className={`fixed top-1/2 -translate-y-1/2 z-50 bg-orange-500 hover:bg-orange-600 text-white p-3 shadow-lg transition-all ${
            hideCampaignsList 
              ? 'left-4 rounded-lg' 
              : 'left-[564px] rounded-lg'
          }`}
          title={hideCampaignsList ? 'Mostrar lista de campañas' : 'Ocultar lista de campañas'}
        >
          {hideCampaignsList ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      )}

      {/* Panel derecho - Visualización de datos o mapa */}
      <div className={`flex-1 relative overflow-hidden ${
        selectedCampaignForViewer && hideCampaignsList ? 'flex items-center justify-center' : ''
      }`}>
        {selectedCampaignForViewer ? (
          <div className={hideCampaignsList ? 'w-full max-w-screen-2xl h-full px-4' : 'w-full h-full'}>
            <CampaignDataViewer
              campaignId={selectedCampaignForViewer.campaign.id}
              campaignName={selectedCampaignForViewer.campaign.name}
              sensors={selectedCampaignForViewer.sensors}
              allSensors={sensors}
              onClose={() => setSelectedCampaignForViewer(null)}
            />
          </div>
        ) : (
          <>
            {/* Mapa cuando no hay campaña seleccionada */}
            <MapContainer
              center={[4.6097, -74.0817]}
              zoom={6}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              {sensors.map((sensor) => (
                <Marker
                  key={sensor.mac}
                  position={[sensor.lat || 0, sensor.lng || 0]}
                  icon={L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background: ${sensor.status === 'active' ? '#10b981' : '#6b7280'}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                    iconSize: [12, 12],
                    iconAnchor: [6, 6]
                  })}
                >
                  <Popup>
                    <strong>{sensor.name}</strong>
                    <br />
                    <small>{sensor.description || 'Sin descripción'}</small>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
            
            {/* Mensaje de instrucción sobre el mapa */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-white/95 backdrop-blur-sm rounded-lg shadow-lg px-6 py-3 border border-gray-200">
              <p className="text-sm text-gray-700">
                <span className="font-semibold text-orange-600">👁️</span> Selecciona una campaña completada para visualizar sus datos
              </p>
            </div>
          </>
        )}
      </div>

      {/* Modal de Nueva Campaña */}
      {showModal && (
        <CampaignModal
          sensors={sensors}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false);
            loadCampaigns();
          }}
          initialData={prefillData}
        />
      )}

    </div>
  );
}
