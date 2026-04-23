import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

interface User {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: 'administrador' | 'tecnico';
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  loginWithAzure: (accessToken: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  console.log('🔵 [AuthContext] AuthProvider inicializado - Token en localStorage:', token ? 'Presente' : 'null');

  // Configurar interceptor de axios para manejar errores de autenticación
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // Si es error 401 o 403 y NO es el endpoint de login o me (ya manejado)
        if ((error.response?.status === 401 || error.response?.status === 403) && 
            !error.config.url?.includes('/auth/login') &&
            !error.config.url?.includes('/auth/me')) {
          console.warn('⚠️ Error de autenticación detectado. Token puede haber expirado.');
          // Opcional: podrías mostrar un toast/notificación aquí
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  // Configurar axios para incluir el token en todas las peticiones
  useEffect(() => {
    console.log('🔵 [AuthContext] useEffect [token] - Token:', token ? 'Presente' : 'null', ', isInitialLoad:', isInitialLoad);
    
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      console.log('🔵 [AuthContext] Token configurado en axios headers');
      
      // Solo intentar obtener el usuario en la carga inicial
      // No cuando hacemos login (porque ya tenemos el usuario)
      if (isInitialLoad) {
        console.log('🔵 [AuthContext] Es carga inicial, obteniendo usuario actual...');
        fetchCurrentUser();
        setIsInitialLoad(false);
      } else {
        console.log('🔵 [AuthContext] No es carga inicial, estableciendo loading = false');
        setLoading(false);
      }
    } else {
      console.log('⚠️ [AuthContext] No hay token, removiendo authorization header');
      delete axios.defaults.headers.common['Authorization'];
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
      const response = await axios.get(`${API_BASE_URL}/auth/me`);
      // El backend ahora retorna el usuario directamente
      setUser(response.data);
      setLoading(false);
    } catch (error: any) {
      console.error('Error fetching current user:', error);
      // Si es error 403 (token expirado) o 401 (no autorizado), limpiar el token
      if (error.response?.status === 403 || error.response?.status === 401) {
        console.warn('⚠️ Sesión expirada o token inválido. Cerrando sesión...');
        logout();
      }
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password
      });

      const { token: newToken, user: userData } = response.data;
      
      handleLoginSuccess(newToken, userData);
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const loginWithAzure = async (accessToken: string) => {
    try {
      console.log('🔵 [AuthContext] loginWithAzure - Iniciando...');
      console.log('🔵 [AuthContext] Enviando token a /api/auth/azure-login');
      
      const response = await axios.post('/api/auth/azure-login', {
        access_token: accessToken
      });

      console.log('🔵 [AuthContext] Respuesta del backend recibida:', response.status);
      const { token: newToken, user: userData } = response.data;
      
      console.log('🔵 [AuthContext] Token del backend:', newToken ? 'Recibido' : 'NO recibido');
      console.log('🔵 [AuthContext] Datos del usuario:', userData);
      console.log('🔵 [AuthContext] Llamando handleLoginSuccess...');
      
      handleLoginSuccess(newToken, userData);
      
      console.log('✅ [AuthContext] loginWithAzure completado exitosamente');
    } catch (error) {
      console.error('❌ [AuthContext] Error en loginWithAzure:', error);
      throw error;
    }
  };

  const handleLoginSuccess = (newToken: string, userData: User) => {
    console.log('🔵 [AuthContext] handleLoginSuccess - Iniciando...');
    console.log('🔵 [AuthContext] Token a guardar:', newToken.substring(0, 50) + '...');
    console.log('🔵 [AuthContext] Usuario:', userData.username, '/', userData.email, '/', userData.role);
    
    // Guardar token en localStorage
    localStorage.setItem('token', newToken);
    console.log('🔵 [AuthContext] Token guardado en localStorage');
    
    // Configurar axios con el nuevo token
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    console.log('🔵 [AuthContext] Token configurado en axios');
    
    setUser(userData);
    console.log('🔵 [AuthContext] setUser ejecutado');
    
    setIsInitialLoad(false);
    console.log('🔵 [AuthContext] setIsInitialLoad(false) ejecutado');
    
    setLoading(false);
    console.log('🔵 [AuthContext] setLoading(false) ejecutado');
    
    setToken(newToken);
    console.log('✅ [AuthContext] handleLoginSuccess completado. Estado actualizado.');
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    loginWithAzure,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'administrador',
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
