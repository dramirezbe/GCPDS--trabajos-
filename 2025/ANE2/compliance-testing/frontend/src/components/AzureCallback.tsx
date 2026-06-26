import { useEffect, useState } from 'react';
import { useMsal } from '@azure/msal-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

/**
 * Componente que maneja el callback después del redirect de Azure AD
 */
const AzureCallback: React.FC = () => {
  console.log('🟢 [AzureCallback] Componente renderizado');
  
  const { instance } = useMsal();
  const { loginWithAzure, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(true);

  console.log('🔵 [AzureCallback] Estado inicial - isProcessing:', true, ', isAuthenticated:', isAuthenticated);

  useEffect(() => {
    console.log('🔵 [AzureCallback] Iniciando procesamiento...');
    
    const handleAuthentication = async () => {
      try {
        // Buscar token guardado por main.tsx
        const pendingToken = sessionStorage.getItem('azure_pending_token');
        
        if (pendingToken) {
          console.log('✅ [AzureCallback] Token encontrado en sessionStorage');
          console.log('🔵 [AzureCallback] Token:', pendingToken.substring(0, 50) + '...');
          console.log('🔵 [AzureCallback] Removiendo token temporal de sessionStorage...');
          sessionStorage.removeItem('azure_pending_token');
          
          console.log('🔵 [AzureCallback] Llamando loginWithAzure...');
          await loginWithAzure(pendingToken);
          
          console.log('✅ [AzureCallback] loginWithAzure completado exitosamente');
          setIsProcessing(false);
        } else {
          // Si no hay token pendiente, intentar obtenerlo de la cuenta activa
          console.log('⚠️ [AzureCallback] No hay token pendiente en sessionStorage');
          const accounts = instance.getAllAccounts();
          console.log('🔵 [AzureCallback] Cuentas Azure encontradas:', accounts.length);
          
          if (accounts.length > 0) {
            console.log('🔵 [AzureCallback] Intentando obtener token silenciosamente...');
            console.log('🔵 [AzureCallback] Cuenta:', accounts[0].username);
            
            try {
              const silentRequest = {
                scopes: ["User.Read", "openid", "profile", "email"],
                account: accounts[0]
              };
              
              const tokenResponse = await instance.acquireTokenSilent(silentRequest);
              console.log('✅ [AzureCallback] Token obtenido silenciosamente');
              console.log('🔵 [AzureCallback] Access Token:', tokenResponse.accessToken.substring(0, 50) + '...');
              console.log('🔵 [AzureCallback] Llamando loginWithAzure...');
              
              await loginWithAzure(tokenResponse.accessToken);
              
              console.log('✅ [AzureCallback] loginWithAzure completado exitosamente');
              setIsProcessing(false);
            } catch (silentError) {
              console.error('❌ [AzureCallback] Error obteniendo token silenciosamente:', silentError);
              console.log('⚠️ [AzureCallback] Redirigiendo al inicio...');
              setIsProcessing(false);
              navigate('/');
            }
          } else {
            console.log('⚠️ [AzureCallback] No hay cuentas de Azure disponibles');
            console.log('🔵 [AzureCallback] Redirigiendo al inicio...');
            setIsProcessing(false);
            navigate('/');
          }
        }
      } catch (error) {
        console.error('❌ [AzureCallback] Error procesando autenticación:', error);
        setIsProcessing(false);
        navigate('/', { state: { error: 'Error al procesar autenticación con Azure AD' } });
      }
    };

    handleAuthentication();
  }, [instance, loginWithAzure, navigate]);

  // Cuando termine de procesar Y el usuario esté autenticado, redirigir
  useEffect(() => {
    console.log('🔵 [AzureCallback] Estado - isProcessing:', isProcessing, ', isAuthenticated:', isAuthenticated);
    
    if (!isProcessing && isAuthenticated) {
      console.log('✅ [AzureCallback] Usuario autenticado y procesamiento completo. Redirigiendo a dashboard...');
      navigate('/');
    } else if (!isProcessing && !isAuthenticated) {
      console.log('⚠️ [AzureCallback] Procesamiento completo pero usuario NO autenticado');
    }
  }, [isProcessing, isAuthenticated, navigate]);

  console.log('🔵 [AzureCallback] Renderizando UI - isProcessing:', isProcessing);

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      flexDirection: 'column',
      backgroundColor: '#f0f0f0'
    }}>
      <div className="spinner" style={{ marginBottom: '20px', fontSize: '48px' }}>🔄</div>
      <h2 style={{ marginBottom: '10px' }}>Procesando autenticación</h2>
      <p>Autenticando con Microsoft Azure...</p>
      <p style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        {isProcessing ? 'Verificando credenciales...' : 'Redirigiendo...'}
      </p>
    </div>
  );
};

export default AzureCallback;
