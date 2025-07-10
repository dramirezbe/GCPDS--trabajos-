from random import randint

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Temperature vs time dynamic plot
        self.plot_graph = pg.PlotWidget()
        self.setCentralWidget(self.plot_graph)
        self.plot_graph.setBackground("w")
        pen = pg.mkPen(color=(255, 0, 0))
        self.plot_graph.setTitle("Temperature vs Time", color="b", size="20pt")
        styles = {"color": "red", "font-size": "18px"}
        self.plot_graph.setLabel("left", "Temperature (°C)", **styles)
        self.plot_graph.setLabel("bottom", "Time (min)", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)
        self.plot_graph.setYRange(20, 40)
        
        # Initialize time and temperature data
        self.num_points = 10 # Number of data points to display
        self.time = list(range(self.num_points))
        self.temperature = [randint(20, 40) for _ in range(self.num_points)]
        
        # Get a line reference
        self.line = self.plot_graph.plot(
            self.time,
            self.temperature,
            name="Temperature Sensor",
            pen=pen,
            symbol="+",
            symbolSize=15,
            symbolBrush="b",
        )
        
        # Add a timer to simulate new temperature measurements
        self.timer = QtCore.QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    def update_plot(self):
        # Generate entirely new data for time and temperature
        self.time = list(range(self.num_points))
        self.temperature = [randint(20, 40) for _ in range(self.num_points)]
        
        # Update the plot with the new, static data
        self.line.setData(self.time, self.temperature)

app = QtWidgets.QApplication([])
main = MainWindow()
main.show()
app.exec()