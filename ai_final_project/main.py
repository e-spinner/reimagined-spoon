import sys

from PySide6.QtWidgets import QApplication

from ai_final_project.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Homework Grader")
    app.setOrganizationName("AI Final Project")
    base = app.font()
    base.setPointSize(max(base.pointSize(), 10))
    app.setFont(base)

    window = MainWindow()
    window.show()

    return app.exec()
