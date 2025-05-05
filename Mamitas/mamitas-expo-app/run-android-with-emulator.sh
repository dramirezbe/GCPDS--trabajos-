#!/bin/bash

# Configurar la plataforma gráfica para el emulador
export QT_QPA_PLATFORM=xcb

# Iniciar el emulador en segundo plano
emulator -avd Pixel34_AVD &

# Esperar a que el emulador termine de arrancar
adb wait-for-device
while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
    echo "Esperando a que el emulador termine de arrancar..."
    sleep 2
done

# Ejecutar el comando de Expo para Android
npx expo run:android

