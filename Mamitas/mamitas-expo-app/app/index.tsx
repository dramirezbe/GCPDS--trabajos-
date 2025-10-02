// index.tsx
import * as ImagePicker from 'expo-image-picker';
import React, { useState } from 'react';
import { Button, Image, ScrollView, StyleSheet, Text } from 'react-native';
import { extraerNumeros, extraerTextoOCR, recortarZona } from '../utils/process_image';

export default function App() {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [croppedUri, setCroppedUri] = useState<string | null>(null);
  const [ocrText, setOcrText] = useState<string>('');
  const [numbers, setNumbers] = useState<string[]>([]);

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 1,
    });
    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
    }
  };

  const processImage = async () => {
    if (!imageUri) return;
    // Ejemplo: recortar centro de 200x200
    const x = 50, y = 50, w = 200, h = 200;
    const uriCropped = await recortarZona(imageUri, x, y, w, h);
    setCroppedUri(uriCropped);

    const text = await extraerTextoOCR(uriCropped);
    setOcrText(text);

    const nums = extraerNumeros(text);
    setNumbers(nums);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Button title="Seleccionar imagen" onPress={pickImage} />
      {imageUri && <Image source={{ uri: imageUri }} style={styles.image} />}
      <Button title="Procesar imagen" onPress={processImage} disabled={!imageUri} />
      {croppedUri && (
        <>
          <Text style={styles.label}>Recorte:</Text>
          <Image source={{ uri: croppedUri }} style={styles.image} />
        </>
      )}
      {ocrText ? (
        <>
          <Text style={styles.label}>Texto OCR:</Text>
          <Text style={styles.text}>{ocrText}</Text>
        </>
      ) : null}
      {numbers.length > 0 && (
        <>
          <Text style={styles.label}>Números extraídos:</Text>
          {numbers.map((n, i) => (
            <Text key={i} style={styles.text}>{n}</Text>
          ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, alignItems: 'center' },
  image: { width: 300, height: 300, resizeMode: 'contain', marginVertical: 10 },
  label: { fontWeight: 'bold', marginTop: 15 },
  text: { marginVertical: 5 },
});
