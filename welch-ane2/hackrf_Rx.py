from pyhackrf2 import HackRF
import scipy.signal as sig
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtWidgets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # --- HackRF Parameters ---
        self.SAMPLES = 20e6
        self.CENTER_FREQ = 98e6
        self.VERBOSE = False
        self.NPERSEG = 4096
        self.NOVERLAP = 0.5 * self.NPERSEG # Corrected noverlap calculation for Welch

        # --- HackRF Initialization ---
        self.hackrf = HackRF()
        if self.VERBOSE:
            print("HackRF Found!")
        self.hackrf.sample_rate = self.SAMPLES
        self.hackrf.center_freq = self.CENTER_FREQ

        # --- Matplotlib Plot Setup ---
        self.figure, self.ax = plt.subplots(figsize=(12, 6))
        self.canvas = FigureCanvas(self.figure)
        self.setCentralWidget(self.canvas)

        self.ax.set_title('HackRF Spectrum Analyzer')
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('Power (dBm)')
        self.line, = self.ax.semilogy([], []) # Initialize an empty line for updating

        # --- Timer for Periodic Updates ---
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000) # Update every 1000 ms (1 second)
        self.timer.timeout.connect(self.update_spectrum)
        self.timer.start()

        # Initial plot update
        self.update_spectrum()

    def update_spectrum(self):
        if self.VERBOSE:
            print("Rx Starting...")
        Rx_raw = np.array(self.hackrf.read_samples(int(self.SAMPLES))) # Ensure SAMPLES is int
        if self.VERBOSE:
            print("Rx Done!")
            print(f"Shape = {Rx_raw.shape}")

        if self.VERBOSE:
            print("Welch Starting...")
        # Ensure that noverlap is less than nperseg
        # noverlap is typically a fraction of nperseg, e.g., 0.5 * nperseg
        f_simple, Pxx_simple = sig.welch(Rx_raw, fs=self.SAMPLES, window="hamming", nperseg=self.NPERSEG, noverlap=int(self.NOVERLAP), nfft=self.NPERSEG)
        f = np.fft.fftshift(f_simple)
        Pxx = np.fft.fftshift(Pxx_simple)
        if self.VERBOSE:
            print("Welch Done!")

        print("Updating plot...")

        # Clear previous plot data and draw new data
        self.line.set_data(f, Pxx)
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view() # Autoscale axes
        self.canvas.draw() # Redraw the canvas

        # Save the figure to a file each time it's updated (optional)
        # plt.savefig("spectrum_plot.png")
        # print("Plot saved as 'spectrum_plot.png'")

app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()