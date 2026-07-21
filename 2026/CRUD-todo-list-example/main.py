import sys
from PyQt5.QtWidgets import QApplication
import models
from views import MainWindow
import controllers


def main():
    app = QApplication(sys.argv)
    models.init_db()

    window = MainWindow()

    window.btn_new.clicked.connect(lambda: controllers.on_new_task(window))
    window.btn_edit.clicked.connect(lambda: controllers.on_edit_task(window))
    window.btn_delete.clicked.connect(lambda: controllers.on_delete_task(window))

    controllers._refresh(window)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
