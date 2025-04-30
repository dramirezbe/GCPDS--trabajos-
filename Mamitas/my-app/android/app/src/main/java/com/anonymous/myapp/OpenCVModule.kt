package com.anonymous.myapp

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.imgproc.Imgproc

class OpenCVModule(reactContext: ReactApplicationContext) 
  : ReactContextBaseJavaModule(reactContext) {

  override fun getName(): String = "OpenCVModule"

  @ReactMethod
  fun toGray(base64Image: String, promise: Promise) {
    try {
      // 1) Decodificar Base64 → Bitmap
      val decodedBytes = Base64.decode(base64Image, Base64.DEFAULT)
      val bmp = BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size)

      // 2) Bitmap → Mat
      val srcMat = Mat()
      Utils.bitmapToMat(bmp, srcMat)  // convierte Bitmap a Mat en RGBA :contentReference[oaicite:1]{index=1}

      // 3) Crear Mat vacío para gris y aplicar cvtColor
      val grayMat = Mat()
      Imgproc.cvtColor(srcMat, grayMat, Imgproc.COLOR_BGR2GRAY)  // BGR → Gray :contentReference[oaicite:2]{index=2}

      // 4) Mat gris (CV_8UC1) → Mat en 4 canales para Bitmap (opcional)
      val gray4c = Mat()
      Imgproc.cvtColor(grayMat, gray4c, Imgproc.COLOR_GRAY2RGBA)

      // 5) Mat → Bitmap
      val grayBmp = Bitmap.createBitmap(
        gray4c.cols(), gray4c.rows(),
        Bitmap.Config.ARGB_8888
      )
      Utils.matToBitmap(gray4c, grayBmp)  // convierte Mat de vuelta a Bitmap :contentReference[oaicite:3]{index=3}

      // 6) Re-encodar a Base64
      val outStream = java.io.ByteArrayOutputStream()
      grayBmp.compress(Bitmap.CompressFormat.PNG, 100, outStream)
      val grayBytes = outStream.toByteArray()
      val grayBase64 = Base64.encodeToString(grayBytes, Base64.NO_WRAP)

      promise.resolve(grayBase64)
    } catch (e: Exception) {
      promise.reject("OPENCV_ERROR", e.message)
    }
  }
}
