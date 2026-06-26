import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET;

export interface AuthRequest extends Request {}

// Middleware para verificar token JWT
export const authenticateToken = (req: AuthRequest, res: Response, next: NextFunction) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ error: 'Token no proporcionado' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET) as any;
    req.user = decoded;
    next();
  } catch (error: any) {
    console.error('❌ Error verificando token:', error.message);
    return res.status(403).json({ 
      error: 'Token inválido o expirado',
      message: 'Su sesión ha expirado. Por favor, inicie sesión nuevamente.',
      code: 'TOKEN_EXPIRED'
    });
  }
};

// Middleware para verificar rol de administrador
export const requireAdmin = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (req.user?.role !== 'administrador') {
    return res.status(403).json({ error: 'Acceso denegado. Se requiere rol de administrador.' });
  }
  next();
};

// Middleware para verificar roles permitidos
export const requireRoles = (...allowedRoles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user || !allowedRoles.includes(req.user.role)) {
      return res.status(403).json({ 
        error: 'Acceso denegado. No tiene permisos suficientes.',
        requiredRoles: allowedRoles,
        yourRole: req.user?.role || 'none'
      });
    }
    next();
  };
};
