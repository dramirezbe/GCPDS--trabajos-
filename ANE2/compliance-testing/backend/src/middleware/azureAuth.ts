import { Request, Response, NextFunction } from 'express';
import { jwtVerify, createRemoteJWKSet } from 'jose';

const AZURE_TENANT_ID = process.env.AZURE_TENANT_ID || '8972f9d0-e562-41bc-9ff5-4b09d7bb0688';
const AZURE_CLIENT_ID = process.env.AZURE_CLIENT_ID || '5eeff209-e05e-4fd5-af00-d911b6ca43a9';

// Configurar JWKS endpoint para validación de tokens
const JWKS_URI = `https://login.microsoftonline.com/${AZURE_TENANT_ID}/discovery/v2.0/keys`;
const JWKS = createRemoteJWKSet(new URL(JWKS_URI));

// Issuer esperado para validación
const ISSUER = `https://login.microsoftonline.com/${AZURE_TENANT_ID}/v2.0`;

export interface AzureTokenPayload {
  oid?: string;           // Object ID del usuario
  sub?: string;           // Subject
  preferred_username?: string;  // Email del usuario
  email?: string;         // Email alternativo
  upn?: string;           // User Principal Name
  name?: string;          // Nombre completo
  roles?: string[];       // Roles de aplicación
  groups?: string[];      // Grupos de Azure AD
  aud?: string;           // Audience
  iss?: string;           // Issuer
  exp?: number;           // Expiration time
  iat?: number;           // Issued at time
  [key: string]: any;     // Otros claims
}

/**
 * Middleware para validar tokens de Azure AD
 * Valida la firma, issuer, audience y expiración del token
 */
export async function validateAzureToken(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    // Extraer token del header Authorization
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Token de autorización no proporcionado' });
      return;
    }

    const token = authHeader.substring(7); // Remover 'Bearer '

    try {
      // Validar y verificar el token JWT usando JWKS de Azure AD
      const { payload } = await jwtVerify(token, JWKS, {
        issuer: ISSUER,
        audience: AZURE_CLIENT_ID,
        algorithms: ['RS256'], // Azure AD usa RS256
      });

      // Convertir payload a tipo específico
      const azureUser = payload as AzureTokenPayload;

      // Registrar información de roles/grupos si existen (para auditoría)
      if (azureUser.roles || azureUser.groups) {
        console.log('Azure AD Roles/Groups detected:', {
          email: azureUser.preferred_username || azureUser.email,
          roles: azureUser.roles,
          groups: azureUser.groups,
          oid: azureUser.oid
        });
      }

      // Adjuntar información del usuario al request
      (req as any).azureUser = azureUser;
      
      next();
    } catch (verifyError: any) {
      console.error('Error validando token de Azure:', verifyError.message);
      
      // Mensajes de error específicos
      if (verifyError.code === 'ERR_JWT_EXPIRED') {
        res.status(401).json({ error: 'Token expirado' });
      } else if (verifyError.code === 'ERR_JWT_CLAIM_VALIDATION_FAILED') {
        res.status(401).json({ error: 'Token inválido: validación de claims falló' });
      } else if (verifyError.code === 'ERR_JWS_SIGNATURE_VERIFICATION_FAILED') {
        res.status(401).json({ error: 'Token inválido: firma no válida' });
      } else {
        res.status(401).json({ error: 'Token inválido' });
      }
      return;
    }
  } catch (error: any) {
    console.error('Error en middleware de Azure Auth:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
    return;
  }
}

/**
 * Extrae el email del payload del token de Azure AD
 * Intenta múltiples campos en orden de preferencia
 */
export function getEmailFromAzureToken(azureUser: AzureTokenPayload): string | null {
  return azureUser.preferred_username || 
         azureUser.email || 
         azureUser.upn || 
         null;
}

/**
 * Valida que el token tenga un email válido
 */
export function validateAzureEmail(azureUser: AzureTokenPayload): string {
  const email = getEmailFromAzureToken(azureUser);
  
  if (!email) {
    throw new Error('No se encontró email en el token de Azure AD');
  }
  
  return email;
}
