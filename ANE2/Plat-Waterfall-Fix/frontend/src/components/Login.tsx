import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";
import { Eye, EyeOff, LayoutGrid } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import logoANE from '../images/logo.png';
import '../styles/Login.css';

interface LoginProps {
  showLegacyForm?: boolean;
}

const Login: React.FC<LoginProps> = ({ showLegacyForm = false }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, loginWithAzure } = useAuth();
  const { instance } = useMsal();
  const navigate = useNavigate();

  const handleAzureLogin = async () => {
    setError('');
    setLoading(true);
    try {
      // Usar redirect en lugar de popup para mejor compatibilidad en producción
      await instance.loginRedirect(loginRequest);
    } catch (err: any) {
      console.error("Azure Login Error:", err);
      setError('Error al iniciar sesión con Microsoft Azure');
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-box">
        <div className="logo-container">
          <img src={logoANE} alt="ANE Colombia" className="logo-img" />
        </div>
        
        <h1 className="login-title">Plataforma de sensado espectral</h1>
        
        {error && (
            <div className="error-message" style={{ marginBottom: '15px' }}>
              {error}
            </div>
        )}

        {showLegacyForm ? (
            <form onSubmit={handleSubmit} className="login-form-wrapper">
              <div className="input-wrapper">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Usuario"
                  required
                  autoComplete="username"
                  disabled={loading}
                  className="input-field"
                />
              </div>

              <div className="input-wrapper password-wrapper">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Escribe la contraseña"
                  required
                  autoComplete="current-password"
                  disabled={loading}
                  className="input-field"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-toggle-btn"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              <button type="submit" className="submit-btn" disabled={loading}>
                {loading ? 'Ingresando...' : 'Ingresar en la plataforma'}
              </button>
              
              <div style={{ textAlign: 'center', marginTop: '10px' }}>
                <a href="#" onClick={(e) => { e.preventDefault(); navigate('/'); }} style={{ color: '#666', fontSize: '14px', textDecoration: 'none' }}>
                  &larr; Volver a Ingreso Microsoft
                </a>
              </div>
            </form>
        ) : (
            <div className="login-form-wrapper">
                <button 
                    type="button" 
                    className="azure-btn" 
                    onClick={handleAzureLogin}
                    disabled={loading}
                >
                    <LayoutGrid size={20} />
                    <span>Ingresar con Microsoft Azure</span>
                </button>
                
                <div style={{ textAlign: 'center', marginTop: '20px' }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); navigate('/login'); }} style={{ color: '#999', fontSize: '12px', textDecoration: 'underline' }}>
                        Acceso Administrativo / Legacy
                    </a>
                </div>
            </div>
        )}
      </div>
    </div>
  );
};

export default Login;
