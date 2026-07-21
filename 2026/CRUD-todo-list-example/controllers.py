from PyQt5.QtWidgets import QMessageBox
from views import TaskDialog
import models


def _refresh(main_window):
    tasks = models.get_all_tasks()
    main_window.refresh_table(tasks)


def on_new_task(main_window):
    dialog = TaskDialog(main_window)
    if dialog.exec_() == TaskDialog.Accepted:
        data = dialog.get_data()
        models.create_task(data["title"], data["description"])
        _refresh(main_window)


def on_edit_task(main_window):
    task_id = main_window.selected_task_id()
    if task_id is None:
        QMessageBox.information(main_window, "Info", "Seleccione una tarea para editar.")
        return

    tasks = models.get_all_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return

    dialog = TaskDialog(main_window, task=task)
    if dialog.exec_() == TaskDialog.Accepted:
        data = dialog.get_data()
        models.update_task(task_id, data["title"], data["description"], data["completed"])
        _refresh(main_window)


def on_delete_task(main_window):
    task_id = main_window.selected_task_id()
    if task_id is None:
        QMessageBox.information(main_window, "Info", "Seleccione una tarea para eliminar.")
        return

    reply = QMessageBox.question(
        main_window,
        "Confirmar",
        "Eliminar esta tarea?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply == QMessageBox.Yes:
        models.delete_task(task_id)
        _refresh(main_window)
