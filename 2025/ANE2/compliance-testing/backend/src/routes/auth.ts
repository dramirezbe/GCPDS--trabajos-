import { Router, Response } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { query } from '../database/connection';
import { authenticateToken, requireAdmin, AuthRequest } from '../middleware/auth';
import { validateAzureToken, validateAzureEmail, AzureTokenPayload } from '../middleware/azureAuth';

const router = Router();
const JWT_SECRET = process.env.JWT_SECRET;
const JWT_EXPIRES_IN = '24h';

/**
 * @swagger
 * /api/auth/azure-login:
 *   post:
 *     summary: Iniciar sesión con Azure AD
 *     description: Valida token de Azure AD y genera token JWT de aplicación
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - access_token
 *             properties:
 *               access_token:
 *                 type: string
 *                 description: Access token de Azure AD obtenido desde el frontend
 *     responses:
 *       200:
 *         description: Login exitoso
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 token:
 *                   type: string
 *                   description: JWT token de la aplicación
 *                 user:
 *                   type: object
 *                   properties:
 *                     id:
 *                       type: integer
 *                     username:
 *                       type: string
 *                     full_name:
 *                       type: string
 *                     email:
 *                       type: string
 *                     role:
 *                       type: string
 *       400:
 *         description: Email no encontrado en token
 *       401:
 *         description: Token inválido o usuario no autorizado
 *       500:
 *         description: Error interno del servidor
 */
router.post('/azure-login',
  async (req: any, res: Response, next: any) => {
    // Mover token del body al header para el middleware
    if (req.body.access_token) {
      req.headers.authorization = `Bearer ${req.body.access_token}`;
    }
    next();
  },
  validateAzureToken, // Nuevo middleware usando jose en lugar de passport
  async (req: any, res: Response) => {
    try {
      const azureUser = req.azureUser as AzureTokenPayload;
      
      // Validar y extraer email del token
      const email = validateAzureEmail(azureUser).toLowerCase();

      console.log(`✅ Token válido para: ${email}`);

      // ============================================
      // OPCIÓN 3: Hybrid - Dominio permitido + Auto-registro
      // ============================================

      // Verificar dominio permitido
      const allowedDomains = ['ane.gov.co'];
      const domain = email.split('@')[1];

      if (!allowedDomains.includes(domain)) {
        console.log(`❌ Dominio no autorizado: ${domain}`);
        return res.status(403).json({ 
          error: 'Dominio no autorizado. Solo usuarios de @ane.gov.co pueden acceder.' 
        });
      }

      console.log(`✅ Dominio autorizado: ${domain}`);

      // Buscar usuario en la base de datos
      let result = await query(
        'SELECT id, username, email, full_name, role, is_active FROM users WHERE email = $1',
        [email]
      );

      let user = result.rows[0];

      // Si el usuario no existe, crear automáticamente
      if (!user) {
        console.log(`📝 Usuario no existe. Creando nuevo usuario: ${email}`);
        
        const fullName = azureUser.name || email.split('@')[0];
        const username = email.split('@')[0]; // Parte antes del @
        const defaultRole = 'tecnico'; // Rol por defecto
        const hashedPassword = await bcrypt.hash(Math.random().toString(36), 10); // Password aleatorio (no se usará)

        try {
          result = await query(
            `INSERT INTO users (username, password, email, full_name, role, is_active, created_at, updated_at) 
             VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW()) 
             RETURNING id, username, email, full_name, role, is_active`,
            [username, hashedPassword, email, fullName, defaultRole, true]
          );

          user = result.rows[0];
          console.log(`✅ Usuario creado exitosamente: ${email} (rol: ${defaultRole})`);
          
          // Log de auditoría (opcional, si la tabla existe)
          query(
            `INSERT INTO audit_logs (user_id, action, details, created_at) 
             VALUES ($1, $2, $3, NOW())`,
            [user.id, 'user_auto_created', JSON.stringify({ 
              email, 
              source: 'azure_ad',
              domain 
            })]
          ).catch(err => {
            // Si falla el audit log, solo registrar pero no detener el proceso
            console.warn('⚠️ No se pudo crear audit log:', err.message);
          });

        } catch (createError: any) {
          console.error('❌ Error creando usuario:', createError);
          
          // Si hay error de conflicto (usuario ya existe), intentar obtenerlo de nuevo
          if (createError.code === '23505') { // Código de unique violation en PostgreSQL
            console.log('⚠️ Usuario ya existe (probablemente creado por otra sesión), re-intentando búsqueda...');
            result = await query(
              'SELECT id, username, email, full_name, role, is_active FROM users WHERE email = $1',
              [email]
            );
            user = result.rows[0];
            
            if (!user) {
              return res.status(500).json({ error: 'Error al crear usuario' });
            }
          } else {
            return res.status(500).json({ error: 'Error al crear usuario' });
          }
        }
      } else {
        console.log(`✅ Usuario encontrado: ${email} (rol: ${user.role})`);
      }

      // Verificar que el usuario está activo
      if (!user.is_active) {
        console.log(`❌ Usuario desactivado: ${email}`);
        return res.status(403).json({ 
          error: 'Usuario desactivado. Contacte al administrador.' 
        });
      }

      // Actualizar último login
      query(
        'UPDATE users SET updated_at = NOW() WHERE id = $1',
        [user.id]
      ).catch(err => {
        console.warn('⚠️ No se pudo actualizar último login:', err.message);
      });

      // Generar token JWT local (mismo formato que login normal)
      const token = jwt.sign(
        {
          id: user.id,
          username: user.username,
          role: user.role,
          full_name: user.full_name,
          email: user.email
        },
        JWT_SECRET,
        { expiresIn: JWT_EXPIRES_IN }
      );

      console.log(`✅ JWT generado para: ${email}`);

      res.json({
        token,
        user: {
          id: user.id,
          username: user.username,
          full_name: user.full_name,
          email: user.email,
          role: user.role
        }
      });
    } catch (error: any) {
      console.error('❌ Error en login con Azure AD:', error);
      
      // Manejar errores específicos de validación
      if (error.message.includes('email')) {
        return res.status(400).json({ error: error.message });
      }
      
      res.status(500).json({ error: 'Error al procesar el login de Azure' });
    }
  }
);

/**
 * @swagger
 * /api/auth/login:
 *   post:
 *     summary: Iniciar sesión
 *     description: Autenticar usuario y obtener token JWT
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - username
 *               - password
 *             properties:
 *               username:
 *                 type: string
 *                 example: admin
 *               password:
 *                 type: string
 *                 example: admin123
 *     responses:
 *       200:
 *         description: Login exitoso
 *       401:
 *         description: Credenciales inválidas
 */
router.post('/login', async (req: any, res: Response) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Usuario y contraseña son requeridos' });
    }

    // Buscar usuario
    const result = await query(
      'SELECT * FROM users WHERE username = $1 AND is_active = TRUE',
      [username]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Usuario o contraseña incorrectos' });
    }

    const user = result.rows[0];

    // Verificar contraseña
    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: 'Usuario o contraseña incorrectos' });
    }

    // Generar token JWT
    const token = jwt.sign(
      {
        id: user.id,
        username: user.username,
        role: user.role,
        full_name: user.full_name,
        email: user.email
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        full_name: user.full_name,
        email: user.email,
        role: user.role
      }
    });
  } catch (error: any) {
    console.error('Error en login:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/me:
 *   get:
 *     summary: Obtener información del usuario actual
 *     description: Retorna los datos del usuario autenticado
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Información del usuario
 *       401:
 *         description: No autenticado
 */
router.get('/me', authenticateToken, async (req: AuthRequest, res: Response) => {
  try {
    // Buscar el usuario completo en la base de datos
    const result = await query(
      'SELECT id, username, full_name, email, role, is_active FROM users WHERE id = $1',
      [req.user?.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Usuario no encontrado' });
    }

    res.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error obteniendo usuario:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/users:
 *   get:
 *     summary: Listar todos los usuarios
 *     description: Obtener lista de usuarios (solo administradores)
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Lista de usuarios
 *       403:
 *         description: Acceso denegado
 */
router.get('/users', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    const result = await query(`
      SELECT id, username, full_name, email, role, is_active, created_at, updated_at
      FROM users
      ORDER BY created_at DESC
    `);

    res.json(result.rows);
  } catch (error: any) {
    console.error('Error listando usuarios:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/users:
 *   post:
 *     summary: Crear nuevo usuario
 *     description: Crear un nuevo usuario (solo administradores)
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - username
 *               - password
 *               - full_name
 *               - email
 *               - role
 *             properties:
 *               username:
 *                 type: string
 *               password:
 *                 type: string
 *               full_name:
 *                 type: string
 *               email:
 *                 type: string
 *               role:
 *                 type: string
 *                 enum: [administrador, tecnico]
 *     responses:
 *       201:
 *         description: Usuario creado
 *       400:
 *         description: Datos inválidos
 *       403:
 *         description: Acceso denegado
 */
router.post('/users', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    const { username, password, full_name, email, role } = req.body;

    // Validar campos requeridos
    if (!username || !password || !full_name || !email || !role) {
      return res.status(400).json({ error: 'Todos los campos son requeridos' });
    }

    // Validar rol
    if (!['administrador', 'tecnico'].includes(role)) {
      return res.status(400).json({ error: 'Rol inválido. Debe ser "administrador" o "tecnico"' });
    }

    // Hashear contraseña
    const hashedPassword = await bcrypt.hash(password, 10);

    // Insertar usuario
    const result = await query(`
      INSERT INTO users (username, password, full_name, email, role)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING id, username, full_name, email, role, is_active, created_at
    `, [username, hashedPassword, full_name, email, role]);

    res.status(201).json(result.rows[0]);
  } catch (error: any) {
    if (error.code === '23505') { // Unique violation
      return res.status(400).json({ error: 'El usuario o email ya existe' });
    }
    console.error('Error creando usuario:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/users/{id}:
 *   put:
 *     summary: Actualizar usuario
 *     description: Actualizar datos de un usuario (solo administradores)
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               full_name:
 *                 type: string
 *               email:
 *                 type: string
 *               role:
 *                 type: string
 *               is_active:
 *                 type: boolean
 *               password:
 *                 type: string
 *     responses:
 *       200:
 *         description: Usuario actualizado
 *       403:
 *         description: Acceso denegado
 */
router.put('/users/:id', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    const { id } = req.params;
    const { full_name, email, role, is_active, password } = req.body;

    const updates: string[] = [];
    const values: any[] = [];
    let paramCount = 1;

    if (full_name !== undefined) {
      updates.push(`full_name = $${paramCount++}`);
      values.push(full_name);
    }
    if (email !== undefined) {
      updates.push(`email = $${paramCount++}`);
      values.push(email);
    }
    if (role !== undefined) {
      if (!['administrador', 'tecnico'].includes(role)) {
        return res.status(400).json({ error: 'Rol inválido' });
      }
      updates.push(`role = $${paramCount++}`);
      values.push(role);
    }
    if (is_active !== undefined) {
      updates.push(`is_active = $${paramCount++}`);
      values.push(is_active);
    }
    if (password) {
      const hashedPassword = await bcrypt.hash(password, 10);
      updates.push(`password = $${paramCount++}`);
      values.push(hashedPassword);
    }

    if (updates.length === 0) {
      return res.status(400).json({ error: 'No hay campos para actualizar' });
    }

    updates.push(`updated_at = NOW()`);
    values.push(id);

    const result = await query(`
      UPDATE users
      SET ${updates.join(', ')}
      WHERE id = $${paramCount}
      RETURNING id, username, full_name, email, role, is_active, updated_at
    `, values);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Usuario no encontrado' });
    }

    res.json(result.rows[0]);
  } catch (error: any) {
    console.error('Error actualizando usuario:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/change-password:
 *   post:
 *     summary: Cambiar contraseña propia
 *     description: Permite al usuario cambiar su propia contraseña
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - currentPassword
 *               - newPassword
 *             properties:
 *               currentPassword:
 *                 type: string
 *               newPassword:
 *                 type: string
 *     responses:
 *       200:
 *         description: Contraseña actualizada
 *       401:
 *         description: Contraseña actual incorrecta
 */
router.post('/change-password', authenticateToken, async (req: any, res: Response) => {
  try {
    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({ error: 'Contraseña actual y nueva son requeridas' });
    }

    // Obtener usuario actual
    const result = await query('SELECT * FROM users WHERE id = $1', [req.user!.id]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Usuario no encontrado' });
    }

    const user = result.rows[0];

    // Verificar contraseña actual
    const validPassword = await bcrypt.compare(currentPassword, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: 'Contraseña actual incorrecta' });
    }

    // Hashear nueva contraseña
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    // Actualizar contraseña
    await query(
      'UPDATE users SET password = $1, updated_at = NOW() WHERE id = $2',
      [hashedPassword, req.user!.id]
    );

    res.json({ message: 'Contraseña actualizada exitosamente' });
  } catch (error: any) {
    console.error('Error cambiando contraseña:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/auth/users/{id}:
 *   delete:
 *     summary: Eliminar usuario
 *     description: Elimina un usuario del sistema (solo administradores)
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Usuario eliminado
 *       403:
 *         description: Acceso denegado
 *       404:
 *         description: Usuario no encontrado
 */
router.delete('/users/:id', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    const userId = parseInt(req.params.id);

    // No permitir que el admin se elimine a sí mismo
    if (userId === req.user?.id) {
      return res.status(400).json({ error: 'No puedes eliminar tu propio usuario' });
    }

    const result = await query('DELETE FROM users WHERE id = $1 RETURNING id', [userId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Usuario no encontrado' });
    }

    res.json({ message: 'Usuario eliminado exitosamente' });
  } catch (error: any) {
    console.error('Error eliminando usuario:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
