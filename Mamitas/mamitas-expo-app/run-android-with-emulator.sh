#!/usr/bin/env bash
# Nombre: run-android-with-emulator.sh
# Descripción: Arranca el emulador con QT_QPA_PLATFORM=xcb y luego ejecuta react-native.

# 1. Define el nombre de tu AVD
AVD_NAME="Pixel34_AVD"

# 2. Exporta la variable para Qt
export QT_QPA_PLATFORM=xcb

# 3. Arranca el emulador en segundo plano, redirigiendo logs
echo "Iniciando el emulador $AVD_NAME con QT_QPA_PLATFORM=$QT_QPA_PLATFORM..."
/opt/android-sdk/emulator/emulator -avd "$AVD_NAME" -no-snapshot-load > /dev/null 2>&1 &

EMULATOR_PID=$!
echo "Emulador iniciado (PID $EMULATOR_PID). Esperando a que esté listo..."

# 4. Espera a que el emulador aparezca en adb
until adb shell getprop sys.boot_completed | grep -m 1 '1' > /dev/null; do
  sleep 2
done
echo "Emulador listo."

# 5. Corre React Native
echo "Ejecutando npx react-native run-android..."
npx expo run:android


