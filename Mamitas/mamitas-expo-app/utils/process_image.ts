// process_image.tsx
import TextRecognition from '@react-native-ml-kit/text-recognition';
import * as ImageManipulator from 'expo-image-manipulator';

/**
 * Recorta una zona de la imagen especificada por x, y, w, h usando expo-image-manipulator
 * @param imageUri URI de la imagen original
 * @param x coordenada X del origen del recorte
 * @param y coordenada Y del origen del recorte
 * @param w ancho del recorte
 * @param h alto del recorte
 * @returns Promise<string> URI de la imagen recortada
 */
export async function recortarZona(
  imageUri: string,
  x: number,
  y: number,
  w: number,
  h: number
): Promise<string> {
  const manipResult = await ImageManipulator.manipulateAsync(
    imageUri,
    [{ crop: { originX: x, originY: y, width: w, height: h } }],
    { format: ImageManipulator.SaveFormat.PNG }
  );
  return manipResult.uri;
}

/**
 * Extrae texto OCR usando ML Kit
 * @param imageUri URI de la imagen (puede ser recortada)
 * @returns Promise<string> texto reconocido
 */
export async function extraerTextoOCR(imageUri: string): Promise<string> {
  const result = await TextRecognition.recognize(imageUri);
  return result.text;
}

/**
 * Extrae números (enteros o flotantes) de un texto
 * @param texto cadena de texto donde buscar números
 * @returns array de strings con los números encontrados
 */
export function extraerNumeros(texto: string): string[] {
  const regex = /\d+(?:\.\d+)?/g;
  const matches = texto.match(regex);
  return matches ?? [];
}
