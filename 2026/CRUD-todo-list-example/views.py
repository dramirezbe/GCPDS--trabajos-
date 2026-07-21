from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QStatusBar,
    QDialog,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Nueva Tarea" if task is None else "Editar Tarea")
        self.setMinimumWidth(400)

        self.title_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.completed_check = QCheckBox("Completada")

        if task is not None:
            self.title_edit.setText(task["title"])
            self.description_edit.setText(task["description"])
            self.completed_check.setChecked(bool(task["completed"]))

        form_layout = QFormLayout()
        form_layout.addRow("Titulo:", self.title_edit)
        form_layout.addRow("Descripcion:", self.description_edit)
        form_layout.addRow("", self.completed_check)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Error", "El titulo es obligatorio.")
            self.title_edit.setFocus()
            return
        super().accept()

    def get_data(self):
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "completed": self.completed_check.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Todo List")
        self.setMinimumSize(600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Titulo", "Descripcion", "Estado", "Creado"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.btn_new = QPushButton("Nueva Tarea")
        self.btn_edit = QPushButton("Editar")
        self.btn_delete = QPushButton("Eliminar")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_new)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        central_widget.setLayout(layout)

    def refresh_table(self, tasks):
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(task["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(task["description"]))
            estado = "Completada" if task["completed"] else "Pendiente"
            self.table.setItem(row, 2, QTableWidgetItem(estado))
            self.table.setItem(row, 3, QTableWidgetItem(task["created_at"]))
            self.table.item(row, 0).setData(Qt.UserRole, task["id"])
        count = len(tasks)
        self.status_bar.showMessage(
            f"{count} tarea{'s' if count != 1 else ''}"
        )

    def selected_task_id(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            return None
        item = self.table.item(current_row, 0)
        return item.data(Qt.UserRole) if item else None
