import sys
import multiprocessing as mp

from PySide6.QtWidgets import QApplication

from ai_final_project.ui.main_window import MainWindow


def main() -> int:
    # Required for frozen executables (PyInstaller/AppImage) when OCR backends
    # spin worker processes; prevents child workers from relaunching the GUI.
    mp.freeze_support()

    app = QApplication(sys.argv)
    app.setApplicationName("Homework Grader")
    app.setOrganizationName("AI Final Project")
    base = app.font()
    base.setPointSize(max(base.pointSize(), 10))
    app.setFont(base)

    window = MainWindow()
    window.show()

    return app.exec()
