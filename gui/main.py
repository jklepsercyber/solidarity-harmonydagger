"""HarmonyDagger GUI - entry point."""
import sys
from pathlib import Path

# Make the project root importable so harmonydagger package resolves
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Solidarity - Based on HarmonyDagger")
    app.setApplicationDisplayName("Solidarity - Based on HarmonyDagger")
    app.setApplicationVersion("0.4.0")
    app.setOrganizationName("Jordan Klepser")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
