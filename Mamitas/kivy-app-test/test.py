import kivy
from kivy.app import App
from kivy.uix.label import Label

import tflite_runtime
import numpy as np
import cv2
import re
import pytesseract
import os
import matplotlib
import json
import scipy

print("--------------------Init Workspace---------------------")

class MyApp(App):

    def build(self):
        # Obtener versiones
        versions = {
            "kivy": kivy.__version__,
            "tflite_runtime": tflite_runtime.__version__,
            "numpy": np.__version__,
            "opencv-python": cv2.__version__,
            "pytesseract": pytesseract.get_tesseract_version(),  # opcional
            "matplotlib": matplotlib.__version__,
            "scipy": scipy.__version__,
        }

        # Crear el texto con las versiones
        version_text = "\n".join([f"{k}: {v}" for k, v in versions.items()])

        return Label(text=version_text)


if __name__ == '__main__':
    MyApp().run()
