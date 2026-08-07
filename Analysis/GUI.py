import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
)

from Main_Analysis import analyze_files
from PySide6.QtCore import (
    QObject,
    QThread,
    Signal
)

class AnalysisWorker(QObject):

    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, int, str)

    def __init__(
        self,
        selected_files,
        output_folder,
        run_sj,
        run_toj,
        run_srt,
        qc_settings
    ):
        super().__init__()

        self.selected_files = selected_files
        self.output_folder = output_folder

        self.run_sj = run_sj
        self.run_toj = run_toj
        self.run_srt = run_srt

        # Store QC settings
        self.qc_settings = qc_settings

    def run(self):

        try:

            results = analyze_files(
                self.selected_files,
                output_folder=self.output_folder,
                run_sj=self.run_sj,
                run_toj=self.run_toj,
                run_srt=self.run_srt,
                progress_callback=self.report_progress,
                **self.qc_settings
            )

            self.finished.emit(results)

        except Exception as error:

            self.error.emit(
                str(error)
            )

    def report_progress(
        self,
        current,
        total,
        filename
    ):

        self.progress.emit(
            current,
            total,
            filename
        )

class MSIAnalysisGUI(QWidget):

    # ==================================================
    # Initialize GUI
    # ==================================================

    def __init__(self):
        super().__init__()

        self.selected_files = []
        self.output_folder = "Results"

        self.setWindowTitle("MSI Analysis Suite")
        self.resize(700, 550)

        self.setup_ui()

    # ==================================================
    # Build GUI
    # ==================================================

    def setup_ui(self):

        main_layout = QVBoxLayout()

        # -------------------------
        # Title
        # -------------------------

        title = QLabel("MSI Analysis Suite")

        title.setStyleSheet(
            "font-size: 24px; "
            "font-weight: bold;"
        )

        main_layout.addWidget(title)

        # -------------------------
        # Participant selection
        # -------------------------

        participant_label = QLabel(
            "Selected Participant Files"
        )

        main_layout.addWidget(participant_label)

        self.file_list = QListWidget()

        main_layout.addWidget(self.file_list)

        file_button_layout = QHBoxLayout()

        self.select_button = QPushButton(
            "Select Participants"
        )

        self.clear_button = QPushButton(
            "Clear Selection"
        )

        file_button_layout.addWidget(
            self.select_button
        )

        file_button_layout.addWidget(
            self.clear_button
        )

        main_layout.addLayout(
            file_button_layout
        )

        # -------------------------
        # Analysis selection
        # -------------------------

        analysis_title = QLabel(
            "Analyses"
        )

        analysis_title.setStyleSheet(
            "font-weight: bold;"
        )

        main_layout.addWidget(
            analysis_title
        )

        self.sj_checkbox = QCheckBox(
            "Simultaneity Judgment (SJ)"
        )

        self.toj_checkbox = QCheckBox(
            "Temporal Order Judgment (TOJ)"
        )

        self.srt_checkbox = QCheckBox(
            "Simple Reaction Time (SRT)"
        )

        # Select all analyses by default
        self.sj_checkbox.setChecked(True)
        self.toj_checkbox.setChecked(True)
        self.srt_checkbox.setChecked(True)

        main_layout.addWidget(
            self.sj_checkbox
        )

        main_layout.addWidget(
            self.toj_checkbox
        )

        main_layout.addWidget(
            self.srt_checkbox
        )

        # -------------------------
        # QC Settings
        # -------------------------

        qc_group = QGroupBox(
            "Quality Control Settings"
        )

        qc_layout = QFormLayout()

        # -------------------------
        # SJ / TOJ Settings
        # -------------------------

        self.min_r2_spin = QDoubleSpinBox()
        self.min_r2_spin.setRange(0.0, 1.0)
        self.min_r2_spin.setSingleStep(0.05)
        self.min_r2_spin.setDecimals(2)
        self.min_r2_spin.setValue(0.80)

        qc_layout.addRow(
            "Minimum R²:",
            self.min_r2_spin
        )

        self.min_response_spin = QDoubleSpinBox()
        self.min_response_spin.setRange(0.0, 0.50)
        self.min_response_spin.setSingleStep(0.05)
        self.min_response_spin.setDecimals(2)
        self.min_response_spin.setValue(0.10)

        qc_layout.addRow(
            "Minimum response proportion:",
            self.min_response_spin
        )

        self.max_response_spin = QDoubleSpinBox()
        self.max_response_spin.setRange(0.50, 1.0)
        self.max_response_spin.setSingleStep(0.05)
        self.max_response_spin.setDecimals(2)
        self.max_response_spin.setValue(0.90)

        qc_layout.addRow(
            "Maximum response proportion:",
            self.max_response_spin
        )

        self.max_sigma_spin = QSpinBox()
        self.max_sigma_spin.setRange(1, 5000)
        self.max_sigma_spin.setValue(500)
        self.max_sigma_spin.setSuffix(" ms")

        qc_layout.addRow(
            "Maximum SJ sigma:",
            self.max_sigma_spin
        )

        self.max_slope_spin = QSpinBox()
        self.max_slope_spin.setRange(1, 5000)
        self.max_slope_spin.setValue(500)
        self.max_slope_spin.setSuffix(" ms")

        qc_layout.addRow(
            "Maximum TOJ slope:",
            self.max_slope_spin
        )

        # -------------------------
        # SRT Settings
        # -------------------------

        self.min_rt_spin = QSpinBox()
        self.min_rt_spin.setRange(0, 1000)
        self.min_rt_spin.setValue(100)
        self.min_rt_spin.setSuffix(" ms")

        qc_layout.addRow(
            "Anticipation threshold:",
            self.min_rt_spin
        )

        self.min_valid_srt_spin = QSpinBox()
        self.min_valid_srt_spin.setRange(0, 10000)
        self.min_valid_srt_spin.setValue(250)

        qc_layout.addRow(
            "Minimum valid SRT trials:",
            self.min_valid_srt_spin
        )

        self.max_anticipations_spin = QSpinBox()
        self.max_anticipations_spin.setRange(0, 1000)
        self.max_anticipations_spin.setValue(5)

        qc_layout.addRow(
            "Maximum anticipations:",
            self.max_anticipations_spin
        )

        self.min_mean_rt_spin = QDoubleSpinBox()
        self.min_mean_rt_spin.setRange(0.0, 5.0)
        self.min_mean_rt_spin.setSingleStep(0.05)
        self.min_mean_rt_spin.setDecimals(2)
        self.min_mean_rt_spin.setValue(0.15)
        self.min_mean_rt_spin.setSuffix(" sec")

        qc_layout.addRow(
            "Minimum mean RT:",
            self.min_mean_rt_spin
        )

        self.max_mean_rt_spin = QDoubleSpinBox()
        self.max_mean_rt_spin.setRange(0.0, 10.0)
        self.max_mean_rt_spin.setSingleStep(0.10)
        self.max_mean_rt_spin.setDecimals(2)
        self.max_mean_rt_spin.setValue(1.50)
        self.max_mean_rt_spin.setSuffix(" sec")

        qc_layout.addRow(
            "Maximum mean RT:",
            self.max_mean_rt_spin
        )

        # Reset QC settings button
        self.reset_qc_button = QPushButton(
            "Reset to Defaults"
        )

        qc_layout.addRow(
            self.reset_qc_button
        )

        qc_group.setLayout(qc_layout)

        main_layout.addWidget(qc_group)

        # -------------------------
        # Output folder
        # -------------------------

        output_title = QLabel(
            "Output Folder"
        )

        main_layout.addWidget(output_title)

        self.output_label = QLabel(
            self.output_folder
        )

        main_layout.addWidget(
            self.output_label
        )

        self.output_button = QPushButton(
            "Select Output Folder"
        )

        main_layout.addWidget(
            self.output_button
        )

        self.run_button = QPushButton(
            "Run Analysis"
        )

        self.run_button.setMinimumHeight(45)

        main_layout.addWidget(
            self.run_button
        )

        # -------------------------
        # Progress
        # -------------------------

        self.progress_bar = QProgressBar()

        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        main_layout.addWidget(
            self.progress_bar
        )

        self.progress_detail_label = QLabel(
            ""
        )

        main_layout.addWidget(
            self.progress_detail_label
        )

        # -------------------------
        # Status
        # -------------------------

        self.status_label = QLabel(
            "Ready"
        )

        main_layout.addWidget(
            self.status_label
        )

        # Apply layout
        self.setLayout(main_layout)

        # -------------------------
        # QC Results
        # -------------------------

        results_title = QLabel(
            "Quality Control Results"
        )

        results_title.setStyleSheet(
            "font-weight: bold;"
        )

        main_layout.addWidget(
            results_title
        )

        self.results_table = QTableWidget()

        self.results_table.setColumnCount(5)

        self.results_table.setHorizontalHeaderLabels([
            "Participant",
            "SJ",
            "TOJ",
            "SRT",
            "Overall"
        ])

        self.results_table.setRowCount(0)

        main_layout.addWidget(
            self.results_table
        )

        # -------------------------
        # Button connections
        # -------------------------

        self.select_button.clicked.connect(
            self.select_participants
        )

        self.clear_button.clicked.connect(
            self.clear_selection
        )

        self.output_button.clicked.connect(
            self.select_output_folder
        )

        self.run_button.clicked.connect(
            self.run_analysis
        )

        self.reset_qc_button.clicked.connect(
            self.reset_qc_settings
        )

        self.results_table.cellClicked.connect(
            self.show_qc_details
        )
    # ==================================================
    # Select participants
    # ==================================================

    def select_participants(self):

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Participant CSV Files",
            "../Data",
            "CSV Files (*.csv)"
        )

        if not files:
            return

        self.selected_files = files

        self.file_list.clear()

        for file in files:

            self.file_list.addItem(
                os.path.basename(file)
            )

        self.status_label.setText(
            f"{len(files)} participant(s) selected"
        )

    # ==================================================
    # Clear participants
    # ==================================================

    def clear_selection(self):

        self.selected_files = []

        self.file_list.clear()

        self.status_label.setText(
            "No participants selected"
        )

    # ==================================================
    # Select output folder
    # ==================================================

    def select_output_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder"
        )

        if not folder:
            return

        self.output_folder = folder

        self.output_label.setText(
            folder
        )

    # ==================================================
    # Reset QC Settings
    # ==================================================

    def reset_qc_settings(self):

        # SJ / TOJ defaults
        self.min_r2_spin.setValue(0.80)

        self.min_response_spin.setValue(0.10)

        self.max_response_spin.setValue(0.90)

        self.max_sigma_spin.setValue(500)

        self.max_slope_spin.setValue(500)

        # SRT defaults
        self.min_rt_spin.setValue(100)

        self.min_valid_srt_spin.setValue(250)

        self.max_anticipations_spin.setValue(5)

        self.min_mean_rt_spin.setValue(0.15)

        self.max_mean_rt_spin.setValue(1.50)

        self.status_label.setText(
            "QC settings reset to defaults"
        )

    # ==================================================
    # Run analysis
    # ==================================================

    def run_analysis(self):
        if not self.selected_files:
            QMessageBox.warning(
                self,
                "No Participants Selected",
                "Please select at least one participant CSV file."
            )

            return

        run_sj = self.sj_checkbox.isChecked()
        run_toj = self.toj_checkbox.isChecked()
        run_srt = self.srt_checkbox.isChecked()

        qc_settings = {
            "min_response_proportion":
                self.min_response_spin.value(),

            "max_response_proportion":
                self.max_response_spin.value(),

            "min_r2":
                self.min_r2_spin.value(),

            "max_sigma_ms":
                self.max_sigma_spin.value(),

            "max_slope_ms":
                self.max_slope_spin.value(),

            "min_rt_ms":
                self.min_rt_spin.value(),

            "min_valid_srt_trials":
                self.min_valid_srt_spin.value(),

            "max_anticipations":
                self.max_anticipations_spin.value(),

            "min_mean_rt_sec":
                self.min_mean_rt_spin.value(),

            "max_mean_rt_sec":
                self.max_mean_rt_spin.value()
        }

        if not any([
            run_sj,
            run_toj,
            run_srt
        ]):
            QMessageBox.warning(
                self,
                "No Analysis Selected",
                "Please select at least one analysis."
            )

            return

        # Reset GUI
        self.progress_bar.setValue(0)

        self.progress_detail_label.setText("")

        self.status_label.setText(
            "Running analysis..."
        )

        self.run_button.setEnabled(False)

        # Create thread
        self.thread = QThread()

        # Create worker
        self.worker = AnalysisWorker(
            self.selected_files,
            self.output_folder,
            run_sj,
            run_toj,
            run_srt,
            qc_settings
        )

        # Move worker to thread
        self.worker.moveToThread(
            self.thread
        )

        # Start analysis
        self.thread.started.connect(
            self.worker.run
        )

        # Progress updates
        self.worker.progress.connect(
            self.update_progress
        )

        # Successful completion
        self.worker.finished.connect(
            self.analysis_finished
        )

        # Error handling
        self.worker.error.connect(
            self.analysis_failed
        )

        # Stop thread when finished
        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.error.connect(
            self.thread.quit
        )

        # Clean up worker
        self.worker.finished.connect(
            self.worker.deleteLater
        )

        self.worker.error.connect(
            self.worker.deleteLater
        )

        # Clean up thread
        self.thread.finished.connect(
            self.thread.deleteLater
        )

        # Start thread
        self.thread.start()

    def update_progress(
            self,
            current,
            total,
            filename
    ):
        percent = int(
            (current / total) * 100
        )

        self.progress_bar.setValue(
            percent
        )

        self.progress_detail_label.setText(
            f"Participant {current} of {total}: "
            f"{filename}"
        )

    def analysis_finished(
            self,
            results
    ):

        self.progress_bar.setValue(
            100
        )

        self.populate_results_table(
            results
        )

        self.status_label.setText(
            f"Complete - "
            f"{len(results)} participant(s) analyzed"
        )

        self.run_button.setEnabled(
            True
        )

        QMessageBox.information(
            self,
            "Analysis Complete",
            f"Successfully analyzed "
            f"{len(results)} participant(s).\n\n"
            f"Results saved to:\n"
            f"{self.output_folder}"
        )

    def analysis_failed(
            self,
            error_message
    ):

        self.status_label.setText(
            "Analysis failed"
        )

        self.run_button.setEnabled(
            True
        )

        QMessageBox.critical(
            self,
            "Analysis Error",
            error_message
        )

    # ==================================================
    #Data Chart Creation
    # ==================================================

    def populate_results_table(
            self,
            results
    ):

        self.current_results = results.copy()

        self.results_table.setRowCount(
            len(results)
        )

        for row_index, (_, row) in enumerate(
                results.iterrows()
        ):

            # Participant ID
            participant_id = str(
                row.get(
                    "Participant_ID",
                    ""
                )
            )

            self.results_table.setItem(
                row_index,
                0,
                QTableWidgetItem(
                    participant_id
                )
            )

            # SJ QC
            if "SJ_Fit_OK" in results.columns:

                sj_ok = (
                        bool(row["SJ_Fit_OK"])
                        and bool(
                    row["SJ_Response_Range_OK"]
                )
                        and bool(
                    row["SJ_Response_Bias_OK"]
                )
                )

                sj_status = (
                    "PASS"
                    if sj_ok
                    else "REVIEW"
                )

            else:

                sj_status = "Not Run"

            # TOJ QC
            if "TOJ_Fit_OK" in results.columns:

                toj_ok = (
                        bool(row["TOJ_Fit_OK"])
                        and bool(
                    row["TOJ_Response_Range_OK"]
                )
                        and bool(
                    row["TOJ_Response_Bias_OK"]
                )
                )

                toj_status = (
                    "PASS"
                    if toj_ok
                    else "REVIEW"
                )

            else:

                toj_status = "Not Run"

            # SRT QC
            if "SRT_QC_OK" in results.columns:

                srt_status = (
                    "PASS"
                    if bool(row["SRT_QC_OK"])
                    else "REVIEW"
                )

            else:

                srt_status = "Not Run"

            # Overall QC
            overall_status = (
                "PASS"
                if bool(
                    row["Participant_OK"]
                )
                else "REVIEW"
            )

            # Add statuses to table
            self.results_table.setItem(
                row_index,
                1,
                QTableWidgetItem(
                    sj_status
                )
            )

            self.results_table.setItem(
                row_index,
                2,
                QTableWidgetItem(
                    toj_status
                )
            )

            self.results_table.setItem(
                row_index,
                3,
                QTableWidgetItem(
                    srt_status
                )
            )

            self.results_table.setItem(
                row_index,
                4,
                QTableWidgetItem(
                    overall_status
                )
            )

        # Resize columns to contents
        self.results_table.resizeColumnsToContents()

        self.results_table.setAlternatingRowColors(
            True
        )

        self.results_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

    def show_qc_details(
            self,
            row,
            column
    ):

        # Ignore clicks if no results exist yet
        if not hasattr(
                self,
                "current_results"
        ):
            return

        participant = self.current_results.iloc[row]

        participant_id = participant.get(
            "Participant_ID",
            ""
        )

        # --------------------------------
        # Participant column
        # --------------------------------

        if column == 0:

            message = (
                f"Participant {participant_id}\n\n"
                f"Age: {participant.get('Age', 'N/A')}\n"
                f"Gender: {participant.get('Gender', 'N/A')}\n"
                f"Site: {participant.get('Site', 'N/A')}"
            )

            title = "Participant Information"

        # --------------------------------
        # SJ column
        # --------------------------------

        elif column == 1:

            if "SJ_Fit_OK" not in self.current_results.columns:

                message = "SJ analysis was not run."
                title = "SJ Quality Control"

            else:

                fit_status = (
                    "PASS"
                    if bool(
                        participant["SJ_Fit_OK"]
                    )
                    else "FAIL"
                )

                range_status = (
                    "PASS"
                    if bool(
                        participant[
                            "SJ_Response_Range_OK"
                        ]
                    )
                    else "FAIL"
                )

                bias_status = (
                    "PASS"
                    if bool(
                        participant[
                            "SJ_Response_Bias_OK"
                        ]
                    )
                    else "FAIL"
                )

                message = (
                    f"Participant {participant_id} - SJ QC\n\n"

                    f"Fit quality: {fit_status}\n"
                    f"R²: {participant['SJ_R2']:.3f}\n\n"

                    f"Response range: {range_status}\n"
                    f"Response bias: {bias_status}\n\n"

                    f"Simultaneous responses: "
                    f"{participant['SJ_Simultaneous_Proportion'] * 100:.1f}%\n"

                    f"Not simultaneous responses: "
                    f"{participant['SJ_Not_Simultaneous_Proportion'] * 100:.1f}%\n\n"

                    f"PSS: {participant['SJ_PSS_ms']:.2f} ms\n"
                    f"TBW: {participant['SJ_TBW_ms']:.2f} ms"
                )

                title = "SJ Quality Control"

        # --------------------------------
        # TOJ column
        # --------------------------------

        elif column == 2:

            if "TOJ_Fit_OK" not in self.current_results.columns:

                message = "TOJ analysis was not run."
                title = "TOJ Quality Control"

            else:

                fit_status = (
                    "PASS"
                    if bool(
                        participant["TOJ_Fit_OK"]
                    )
                    else "FAIL"
                )

                range_status = (
                    "PASS"
                    if bool(
                        participant[
                            "TOJ_Response_Range_OK"
                        ]
                    )
                    else "FAIL"
                )

                bias_status = (
                    "PASS"
                    if bool(
                        participant[
                            "TOJ_Response_Bias_OK"
                        ]
                    )
                    else "FAIL"
                )

                message = (
                    f"Participant {participant_id} - TOJ QC\n\n"

                    f"Fit quality: {fit_status}\n"
                    f"R²: {participant['TOJ_R2']:.3f}\n\n"

                    f"Response range: {range_status}\n"
                    f"Response bias: {bias_status}\n\n"

                    f"Audio First: "
                    f"{participant['TOJ_Audio_First_Proportion'] * 100:.1f}%\n"

                    f"Visual First: "
                    f"{participant['TOJ_Visual_First_Proportion'] * 100:.1f}%\n\n"

                    f"PSS: {participant['TOJ_PSS_ms']:.2f} ms\n"
                    f"JND: {participant['TOJ_JND_ms']:.2f} ms"
                )

                title = "TOJ Quality Control"

        # --------------------------------
        # SRT column
        # --------------------------------

        elif column == 3:

            if "SRT_QC_OK" not in self.current_results.columns:

                message = "SRT analysis was not run."
                title = "SRT Quality Control"

            else:

                qc_status = (
                    "PASS"
                    if bool(
                        participant["SRT_QC_OK"]
                    )
                    else "FAIL"
                )

                message = (
                    f"Participant {participant_id} - SRT QC\n\n"

                    f"Overall SRT QC: {qc_status}\n\n"

                    f"Total trials: "
                    f"{participant['SRT_Trials']}\n"

                    f"Valid trials: "
                    f"{participant['SRT_Valid_Trials']}\n"

                    f"Clean trials: "
                    f"{participant['SRT_Clean_Trials']}\n"

                    f"Misses: "
                    f"{participant['SRT_Misses']}\n"

                    f"Anticipations: "
                    f"{participant['SRT_Anticipations']}\n\n"

                    f"Mean RT: "
                    f"{participant['Mean_Adjusted_RT_ms']:.1f} ms\n"

                    f"Median RT: "
                    f"{participant['Median_Adjusted_RT_ms']:.1f} ms\n"

                    f"SD: "
                    f"{participant['SD_Adjusted_RT_ms']:.1f} ms\n"

                    f"CV: "
                    f"{participant['CV_Adjusted_RT']:.3f}"
                )

                title = "SRT Quality Control"

        # --------------------------------
        # Overall column
        # --------------------------------

        elif column == 4:

            overall_status = (
                "PASS"
                if bool(
                    participant["Participant_OK"]
                )
                else "REVIEW"
            )

            message = (
                f"Participant {participant_id}\n\n"
                f"Overall QC: {overall_status}\n\n"
                "Click the SJ, TOJ, or SRT columns "
                "to see individual QC details."
            )

            title = "Overall Quality Control"

        else:

            return

        QMessageBox.information(
            self,
            title,
            message
        )
# ======================================================
# Start application
# ======================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MSIAnalysisGUI()

    window.show()

    sys.exit(app.exec())