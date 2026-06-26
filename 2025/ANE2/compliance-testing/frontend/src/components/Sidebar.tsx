import { Radio, Network, BarChart3, HelpCircle, LogOut, Home, Settings, User, Bell } from 'lucide-react';
import logo from '../images/logo.png';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  user: any;
  onLogout: () => void;
  isAdmin: boolean;
}

export function Sidebar({ activeTab, onTabChange, user, onLogout, isAdmin }: SidebarProps) {
  // Filtrar el menú de configuración si no es admin
  const menuItems = [
    { id: 'inicio', icon: Home, label: 'Inicio' },
    { id: 'dispositivos', icon: Network, label: 'Dispositivos' },
    { id: 'monitoreo', icon: Radio, label: 'Monitoreo' },
    { id: 'campañas', icon: BarChart3, label: 'Campañas' },
    { id: 'alertas', icon: Bell, label: 'Alertas' },
    ...(isAdmin ? [{ id: 'configuracion', icon: Settings, label: 'Configuración' }] : []),
  ];

  const bottomItems = [
    { id: 'ayuda', icon: HelpCircle, label: 'Ayuda' },
  ];

  return (
    <div className="w-48 bg-white border-r border-gray-200 flex flex-col h-screen">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-center">
          <img src={logo} alt="ANE Logo" className="w-32 h-auto" />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={`w-full flex items-center px-4 py-3 text-sm transition-colors ${
              activeTab === item.id
                ? 'bg-orange-50 text-orange-600 border-r-4 border-orange-600'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="border-t border-gray-200">
        {/* Info del usuario */}
        <div className="px-4 py-3 bg-gray-50">
          <div className="flex items-center gap-2 mb-1">
            <User className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-900">{user?.full_name || user?.username}</span>
          </div>
          <div className="text-xs text-gray-500 ml-6">
            {user?.role === 'administrador' ? 'Administrador' : 'Técnico'}
          </div>
        </div>
        
        {/* Botones de ayuda y logout */}
        <div className="py-2">
          {bottomItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className="w-full flex items-center px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.label}
            </button>
          ))}
          <button
            onClick={onLogout}
            className="w-full flex items-center px-4 py-3 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Cerrar sesión
          </button>
        </div>
      </div>
    </div>
  );
}
