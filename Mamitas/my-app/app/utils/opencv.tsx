// app/utils/opencv.tsx

import { NativeModules } from 'react-native';

export interface OpenCVModuleInterface {
  /**
   * Convierte una imagen en Base64 a escala de grises y devuelve el resultado
   * también en Base64 (sin prefijo `data:`).
   */
  toGray(base64Image: string): Promise<string>;
}

// Aseguramos el tipado sobre NativeModules y comprobamos disponibilidad
const { OpenCVModule } = NativeModules as {
  OpenCVModule?: OpenCVModuleInterface;
};

/**
 * Llama al módulo nativo OpenCVModule.toGray.
 * @param base64Image Cadena en Base64 (sin prefijo `data:`)
 * @returns Promesa con Base64 de la imagen en gris
 */
export function toGray(base64Image: string): Promise<string> {
  if (!OpenCVModule || typeof OpenCVModule.toGray !== 'function') {
    return Promise.reject(
      new Error('OpenCVModule no está disponible. ¿Has registrado el paquete y copiado los .so?')
    );
  }
  return OpenCVModule.toGray(base64Image);
}
