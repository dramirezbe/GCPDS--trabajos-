import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Obtiene la ruta de este archivo (services/init_env.js)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Sube un nivel a la carpeta raíz del proyecto (padre de services/)
const rootDir = path.resolve(__dirname, '..');

const examplePath = path.join(rootDir, '.env.example');
const envPath = path.join(rootDir, '.env');

if (fs.existsSync(examplePath)) {
    fs.copyFileSync(examplePath, envPath);
    console.log(`.env creado/actualizado en: ${envPath}`);
} else {
    console.error(`Error: No se encontró el archivo ${examplePath}`);
}