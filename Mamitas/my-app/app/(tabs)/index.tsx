import { Image, StyleSheet, Platform, View, Button, Text } from 'react-native';
import React, { useState } from 'react';

import { HelloWave } from '@/components/HelloWave';
import ParallaxScrollView from '@/components/ParallaxScrollView';
import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';

// 1) Importa tu helper TS
import { toGray } from '@/utils/opencv';

export default function HomeScreen() {
  // 2) Estado para guardar la imagen en gris (base64)
  const [grayBase64, setGrayBase64] = useState<string | null>(null);

  // Simulación de una imagen original en Base64
  const originalBase64 = 'iVBORw0KGgoAAAANSUhEUgAA...'; 

  // 3) Función que dispara la conversión
  const handleConvert = async () => {
    try {
      const gray = await toGray(originalBase64);
      setGrayBase64(gray);
    } catch (e) {
      console.error('Error convirtiendo a gris', e);
    }
  };

  return (
    <ParallaxScrollView
      headerBackgroundColor={{ light: '#A1CEDC', dark: '#1D3D47' }}
      headerImage={
        <Image
          source={require('@/assets/images/partial-react-logo.png')}
          style={styles.reactLogo}
        />
      }>
      {/* … tus bloques actuales … */}

      {/* --------------------------------------------------- */}
      {/* 4) Nuevo bloque: Convertir a gris */}
      <ThemedView style={styles.stepContainer}>
        <ThemedText type="subtitle">Step 4: Convertir imagen</ThemedText>
        <Button title="Convertir a Gris" onPress={handleConvert} />
        {grayBase64 ? (
          <Image
            source={{ uri: `data:image/png;base64,${grayBase64}` }}
            style={{ width: 200, height: 200, marginTop: 12 }}
          />
        ) : (
          <Text style={{ marginTop: 12 }}>Aún no convertido</Text>
        )}
      </ThemedView>
      {/* --------------------------------------------------- */}

    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  stepContainer: {
    gap: 8,
    marginBottom: 16,
    paddingHorizontal: 16,
  },
  reactLogo: {
    height: 178,
    width: 290,
    bottom: 0,
    left: 0,
    position: 'absolute',
  },
});
