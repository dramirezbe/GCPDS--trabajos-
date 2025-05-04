import TextRecognition from "@react-native-ml-kit/text-recognition";
import * as FastOpenCV from "react-native-fast-opencv";

import * as ImagePicker from "expo-image-picker";

import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";

export default function Index() {
  const [importInfo, setImportInfo] = useState("");

  useEffect(() => {
    let fastOpenCVWorks = false;
    let imagePickerWorks = false;
    let textRecognitionWorks = false;

    // Verificamos que la librería FastOpenCV tenga contenido.
    if (FastOpenCV && Object.keys(FastOpenCV).length > 0) {
      fastOpenCVWorks = true;
    }

    // Verificamos que expo-image-picker tenga la función 'requestMediaLibraryPermissionsAsync'
    if (
      ImagePicker &&
      typeof ImagePicker.requestMediaLibraryPermissionsAsync === "function"
    ) {
      imagePickerWorks = true;
    }

    // Verificamos que la función "recognize" de ML Kit esté definida.
    if (TextRecognition && typeof TextRecognition.recognize === "function") {
      textRecognitionWorks = true;
    }

    const info =
      `react-native-fast-opencv: ${fastOpenCVWorks ? "OK" : "Error"}\n` +
      `expo-image-picker: ${imagePickerWorks ? "OK" : "Error"}\n` +
      `@react-native-ml-kit/text-recognition: ${textRecognitionWorks ? "OK" : "Error"}`;

    setImportInfo(info);
  }, []);

  return (
    <View
      style={{
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        padding: 20,
      }}
    >
      <Text style={{ textAlign: "center" }}>{importInfo}</Text>
      <Text style={{ marginTop: 20 }}>Hola Mundo!!!!!</Text>
    </View>
  );
}
