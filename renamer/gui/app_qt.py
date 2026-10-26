from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from renamer.application.pipeline import process_pdf
from renamer.domain.models import FileProcessResult
from renamer.infrastructure.ocr import is_tesseract_available
from renamer.infrastructure.paths import default_output_dir


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(
        self, input_pdf: Path, output_dir: Path, use_ocr: bool, number_digits: int | None
    ) -> None:
        super().__init__()
        self.input_pdf = input_pdf
        self.output_dir = output_dir
        self.use_ocr = use_ocr
        self.number_digits = number_digits

    def run(self) -> None:
        try:
            results = process_pdf(
                input_pdf=self.input_pdf,
                output_dir=self.output_dir,
                use_ocr_fallback=self.use_ocr,
                dry_run=False,
                number_digits=self.number_digits,
                progress_callback=self.progress.emit,
            )
            self.done.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Разделение PDF-справок")
        self.setMinimumWidth(700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        title = QLabel("Разделить PDF на справки по номеру")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit(str(default_output_dir()))
        self.ocr_check = QCheckBox("Использовать OCR (для сканов)")
        self.ocr_check.setChecked(True)
        self.digits_combo = QComboBox()
        self.digits_combo.addItem("Авто (2–6 цифр, смешанные номера)", 0)
        for n in (2, 3, 4, 5, 6):
            self.digits_combo.addItem(str(n), n)
        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: #333333;")
        self.ocr_installed = is_tesseract_available()

        layout.addLayout(self._row("Файл PDF:", self.input_edit, self.choose_input))
        layout.addLayout(self._row("Папка вывода:", self.output_edit, self.choose_output))
        digits_row = QHBoxLayout()
        digits_row.addWidget(QLabel("Цифр в номере справки:"))
        digits_row.addWidget(self.digits_combo)
        digits_row.addStretch(1)
        layout.addLayout(digits_row)
        layout.addWidget(self.ocr_check)

        if not self.ocr_installed:
            self.status_label.setText(self._ocr_missing_message())

        self.run_btn = QPushButton("Разделить PDF")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.run_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Страница", "Номер справки", "Источник", "Проверка", "Файл"]
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setMinimumHeight(180)
        layout.addWidget(self.results_table)

        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.worker: Worker | None = None

    def _row(self, label: str, edit: QLineEdit, cb) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(edit, 1)
        btn = QPushButton("Выбрать...")
        btn.clicked.connect(cb)
        row.addWidget(btn)
        return row

    @staticmethod
    def _ocr_missing_message() -> str:
        if sys.platform == "darwin":
            return "OCR не найден. Для сканов установите Tesseract с русским языком."
        return "OCR не найден — сканы распознаваться не будут."

    def choose_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите PDF-файл", "", "PDF Files (*.pdf)")
        if path:
            self.input_edit.setText(path)

    def choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для результата")
        if path:
            self.output_edit.setText(path)

    def start_processing(self) -> None:
        input_pdf = Path(self.input_edit.text().strip())
        output_text = self.output_edit.text().strip()
        output_dir = Path(output_text) if output_text else Path()
        if not input_pdf.is_file() or input_pdf.suffix.lower() != ".pdf":
            QMessageBox.critical(self, "Ошибка", "Выберите корректный PDF-файл.")
            return
        if not output_text:
            QMessageBox.critical(self, "Ошибка", "Выберите папку для результата.")
            return
        self.results_table.setRowCount(0)

        self.run_btn.setEnabled(False)
        self.status_label.setText("Обработка...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        digits = self.digits_combo.currentData()
        self.worker = Worker(
            input_pdf,
            output_dir,
            self.ocr_check.isChecked(),
            None if not digits else int(digits),
        )
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_progress(self, current: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.progress.setFormat(f"Страница {current} из {total}")
        self.status_label.setText(f"Обработка страницы {current} из {total}...")

    def on_done(self, results: list[FileProcessResult]) -> None:
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        manual_count = sum(1 for result in results if result.manual_review)
        for result in results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            values = (
                str(result.page_index + 1),
                result.certificate_number or "Не найден",
                "OCR" if result.source == "ocr_fallback" else "Текст PDF",
                "Проверить вручную" if result.manual_review else "—",
                result.output_path.name,
            )
            for column, value in enumerate(values):
                self.results_table.setItem(row, column, QTableWidgetItem(value))
        self.results_table.resizeColumnsToContents()
        message = f"Готово. Создано файлов: {len(results)}."
        if manual_count:
            message += f" Требуют ручной проверки: {manual_count}."
        self.status_label.setText(message)
        QMessageBox.information(self, "Готово", message)

    def on_failed(self, error: str) -> None:
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("Ошибка")
        QMessageBox.critical(self, "Ошибка", error)

def run() -> None:
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as exc:
        from renamer.infrastructure.crash import show_crash

        show_crash(exc)
        raise
