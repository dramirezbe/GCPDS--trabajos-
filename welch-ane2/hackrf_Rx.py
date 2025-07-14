import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib import ticker
from PyQt5 import QtCore, QtWidgets
import scipy.signal as sig
from pyhackrf2 import HackRF

# --- Worker Class for background processing ---
class Worker(QtCore.QObject):
    # Define a signal that will carry the processed frequency and power data
    spectrum_ready = QtCore.pyqtSignal(np.ndarray, np.ndarray)

    def __init__(self, hackrf, samples, center_freq, nperseg, noverlap, r_impedance, x_inf_lim, x_sup_lim, verbose):
        super().__init__()
        self.hackrf = hackrf
        self.SAMPLES = samples
        self.CENTER_FREQ = center_freq
        self.NPERSEG = nperseg
        self.NOVERLAP = noverlap
        self.R_IMPEDANCE = r_impedance
        self.X_INF_LIM = x_inf_lim
        self.X_SUP_LIM = x_sup_lim
        self.VERBOSE = verbose
        self._running = True

    @QtCore.pyqtSlot()
    def process_spectrum(self):
        """
        Performs the HackRF data acquisition and spectrum processing in a loop.
        Emits spectrum_ready signal when data is processed.
        """
        while self._running: # Keep running indefinitely or until stopped
            if self.VERBOSE:
                print("Rx Starting...")
            try:
                # Acquire raw IQ samples from HackRF
                Rx_raw = np.array(self.hackrf.read_samples(int(self.SAMPLES)))
                if self.VERBOSE:
                    print("Rx Done!")
                    print(f"Shape = {Rx_raw.shape}")

                if self.VERBOSE:
                    print("Welch Starting...")
                
                # Calculate Power Spectral Density using Welch's method
                _, Pxx_V2_Hz = sig.welch(Rx_raw,
                                         fs=self.SAMPLES, window="hamming",
                                         nperseg=int(self.NPERSEG),
                                         noverlap=int(self.NOVERLAP),
                                         nfft=int(self.NPERSEG),
                                         scaling='density')

                # Shift zero-frequency component to the center
                Pxx_V2_Hz_shifted = np.fft.fftshift(Pxx_V2_Hz)

                # --- dBm Conversion ---
                # 1. Convert V^2/Hz to W/Hz using impedance
                Pxx_W_Hz = Pxx_V2_Hz_shifted / self.R_IMPEDANCE
                # 2. Convert W/Hz to mW/Hz
                Pxx_mW_Hz = Pxx_W_Hz * 1000
                # 3. Convert mW/Hz to dBm/Hz
                Pxx_dBm = 10 * np.log10(Pxx_mW_Hz + 1e-12) # Added a small epsilon for stability
                
                # Generate frequency array for plotting
                f = np.linspace(self.X_INF_LIM, self.X_SUP_LIM, len(Pxx_dBm))

                if self.VERBOSE:
                    print("Welch Done!")

                # Emit the signal with the new data to the main thread
                self.spectrum_ready.emit(f, Pxx_dBm)

            except Exception as e:
                print(f"Error during spectrum processing: {e}")
                # In a production application, you might want to emit an error signal here
            
            # Add a small sleep to prevent 100% CPU usage if processing is extremely fast.
            # This can be removed if maximum throughput is desired and the main thread isn't starved.
            QtCore.QThread.msleep(10) # Sleep for 10 milliseconds

    def stop(self):
        """Signals the worker to stop its processing loop."""
        self._running = False

# --- Main Window Class ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        #----Script Config----
        self.VERBOSE = False

        #----HackRF Config----
        self.SAMPLES = 20e6 # Sample rate
        self.BW = self.SAMPLES # Bandwidth equal to sample rate
        self.CENTER_FREQ = 320e6 # Center frequency (e.g., FM band)
        self.NPERSEG = 4096 # Number of samples per Welch segment
        self.NOVERLAP = self.NPERSEG / 2 # Overlap between segments
        self.R_IMPEDANCE = 50 # Characteristic impedance in ohms

        #----Plotting config-----
        self.X_SPAN = None
        self.X_INF_LIM = (self.CENTER_FREQ - self.BW / 2) / 1e6
        self.X_SUP_LIM = (self.CENTER_FREQ + self.BW / 2) / 1e6
        
        self.Y_INF_LIM = -104 # Lower Y-axis limit (dBm/Hz)
        self.Y_SUP_LIM = -20 # Upper Y-axis limit (dBm/Hz)
        self.Y_SPAN = 1 # Y-axis major tick interval

        # --- HackRF Init ---
        self.hackrf = HackRF()
        if self.VERBOSE:
            print("HackRF Found!")
        self.hackrf.sample_rate = self.SAMPLES
        self.hackrf.center_freq = self.CENTER_FREQ

        # --- Matplotlib Plot Setup ---
        self.figure, self.ax = plt.subplots(figsize=(12, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.setCentralWidget(self.canvas)

        self.ax.set_title('HackRF Spectrum Analyzer')
        self.ax.set_xlabel('Frequency (MHz)')
        self.ax.set_ylabel('Power (dBm/Hz)')

        self.line, = self.ax.plot([], []) # Initialize an empty plot line

        # Define Y axis step (span) & limits
        self.ax.yaxis.set_major_locator(ticker.MultipleLocator(self.Y_SPAN))
        self.ax.set_ylim(self.Y_INF_LIM, self.Y_SUP_LIM)
        
        #----Worker and Thread Setup----
        # 1. Create a QThread object to run the worker in a separate thread
        self.thread = QtCore.QThread()
        # 2. Create a worker object, passing necessary parameters for HackRF and processing
        self.worker = Worker(self.hackrf, self.SAMPLES, self.CENTER_FREQ,
                             self.NPERSEG, self.NOVERLAP, self.R_IMPEDANCE,
                             self.X_INF_LIM, self.X_SUP_LIM, self.VERBOSE)
        
        # 3. Move the worker object to the created thread.
        #    This is crucial: worker methods will now execute in this new thread.
        self.worker.moveToThread(self.thread)

        # 4. Connect signals and slots:
        #    - When the thread starts, tell the worker to begin processing.
        self.thread.started.connect(self.worker.process_spectrum)
        #    - When the worker has new spectrum data, tell the main window to update the plot.
        #      This signal-slot connection is cross-thread safe.
        self.worker.spectrum_ready.connect(self.update_plot_data)

        # 5. Connect cleanup operations for when the thread finishes
        self.thread.finished.connect(self.worker.deleteLater) # Delete worker object
        self.thread.finished.connect(self.thread.deleteLater) # Delete thread object

        # 6. Connect to QApplication's aboutToQuit signal for graceful shutdown
        #    This ensures the worker and thread are stopped when the application is closing.
        app = QtWidgets.QApplication.instance() # Get the QApplication instance
        if app is not None:
            app.aboutToQuit.connect(self.stop_worker_and_thread)

        # 7. Start the thread. This will emit thread.started, triggering worker.process_spectrum.
        self.thread.start()

    def update_plot_data(self, f, Pxx_dBm):
        """
        Slot to receive processed frequency and power data from the worker.
        This method executes in the main GUI thread and safely updates the plot.
        """
        if self.VERBOSE:
            print("Updating plot...")

        # Find and print top N peaks for debugging/monitoring
        Pxx_peaks_sort = np.sort(Pxx_dBm)[::-1]
        print("--------Peaks----------")
        for i in range(min(3, len(Pxx_peaks_sort))): # Print top 3 peaks
            print(f"Peak {i+1}: {Pxx_peaks_sort[i]:.2f} dBm/Hz")

        # Update the plot line with new data
        self.line.set_data(f, Pxx_dBm)
        self.ax.relim()  # Recalculate plot limits based on new data
        self.ax.autoscale_view() # Autoscale axes
        self.canvas.draw() # Redraw the canvas to show updates

    def stop_worker_and_thread(self):
        """
        Gracefully stops the worker's processing loop and terminates the thread
        when the application is shutting down.
        """
        if self.thread.isRunning():
            self.worker.stop() # Tell the worker's internal loop to finish
            self.thread.quit()  # Request the thread to exit its event loop
            self.thread.wait()  # Wait for the thread to actually finish execution before continuing

# --- Application Execution ---
if __name__ == '__main__':
    app = QtWidgets.QApplication([]) # Create the QApplication instance
    main = MainWindow() # Create the main window
    main.show() # Show the main window
    app.exec_() # Start the Qt event loop