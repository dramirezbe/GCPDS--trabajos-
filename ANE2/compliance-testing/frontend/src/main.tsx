import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { PublicClientApplication, EventType } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { msalConfig } from './authConfig';
import { AuthProvider } from './contexts/AuthContext';
import App from './App.tsx';
import Login from './components/Login.tsx';
import AzureCallback from './components/AzureCallback.tsx';
import AudioPage from './pages/AudioPage.tsx';
import './index.css';
import 'leaflet/dist/leaflet.css';

// Crear instancia de MSAL
const msalInstance = new PublicClientApplication(msalConfig);

// Inicializar MSAL y configurar eventos
msalInstance.initialize().then(() => {
  console.log('🔵 [main.tsx] MSAL inicializado');
  
  // Manejar el redirect ANTES de renderizar la aplicación
  msalInstance.handleRedirectPromise()
    .then(async (response) => {
      console.log('🔵 [main.tsx] handleRedirectPromise completado');
      
      if (response && response.idToken) {
        console.log('✅ [main.tsx] Token recibido del redirect de Azure');
        console.log('🔵 [main.tsx] ID Token:', response.idToken.substring(0, 50) + '...');
        console.log('🔵 [main.tsx] Access Token también disponible:', response.accessToken ? 'Sí' : 'No');
        
        // Autenticar INMEDIATAMENTE con el backend usando el ID Token
        try {
          console.log('🔵 [main.tsx] Autenticando con backend usando ID Token...');
          const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
          
          const backendResponse = await fetch(`${API_BASE_URL}/auth/azure-login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              access_token: response.idToken  // Enviar ID Token, no Access Token
            })
          });
          
          if (backendResponse.ok) {
            const data = await backendResponse.json();
            console.log('✅ [main.tsx] Backend respondió exitosamente');
            console.log('🔵 [main.tsx] Usuario:', data.user.username);
            
            // Guardar token en localStorage
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            console.log('✅ [main.tsx] Token y usuario guardados en localStorage');
            
            // Redirigir al home
            console.log('🔵 [main.tsx] Redirigiendo a /...');
            window.location.href = '/';
            return; // No renderizar todavía, esperamos el redirect
          } else {
            console.error('❌ [main.tsx] Backend respondió con error:', backendResponse.status);
            const errorData = await backendResponse.json().catch(() => ({}));
            console.error('❌ [main.tsx] Error data:', errorData);
          }
        } catch (error) {
          console.error('❌ [main.tsx] Error autenticando con backend:', error);
        }
      } else {
        console.log('ℹ️ [main.tsx] No hay token del redirect (normal si es navegación directa)');
      }
      
      // Configurar listener para eventos de autenticación
      msalInstance.addEventCallback((event) => {
        if (event.eventType === EventType.LOGIN_SUCCESS) {
          console.log('✅ Login exitoso con Azure AD');
        }
        if (event.eventType === EventType.ACQUIRE_TOKEN_FAILURE) {
          console.error('❌ Error obteniendo token de Azure AD:', event.error);
        }
        if (event.eventType === EventType.LOGOUT_SUCCESS) {
          console.log('✅ Logout exitoso de Azure AD');
        }
      });

      // Renderizar aplicación
      renderApp();
    })
    .catch((error) => {
      console.error('❌ [main.tsx] Error en handleRedirectPromise:', error);
      // Renderizar de todos modos
      renderApp();
    });

  function renderApp() {
    console.log('🔵 [main.tsx] Renderizando aplicación...');
    
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <MsalProvider instance={msalInstance}>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                {/* Rutas públicas que no requieren autenticación */}
                <Route path="/login" element={<Login showLegacyForm={true} />} />
                <Route path="/azure-callback" element={<AzureCallback />} />
                
                {/* Rutas protegidas */}
                <Route path="/" element={<App />} />
                <Route path="/audio/:sensorId" element={<AudioPage />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </MsalProvider>
      </StrictMode>
    );
  }
}).catch((error) => {
  console.error('Error inicializando MSAL:', error);
  // Mostrar error en la UI
  document.getElementById('root')!.innerHTML = `
    <div style="padding: 20px; color: red;">
      <h2>Error de Inicialización</h2>
      <p>No se pudo inicializar el sistema de autenticación.</p>
      <p>Por favor, contacte al administrador del sistema.</p>
    </div>
  `;
});
