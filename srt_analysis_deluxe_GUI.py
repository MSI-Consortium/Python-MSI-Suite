import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind, linregress
from pingouin import bayesfactor_ttest, anova
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget,
    QLabel, QComboBox, QFormLayout, QHBoxLayout, QMessageBox,QFrame,
    QLineEdit, QRadioButton, QButtonGroup, QDialog, QTextEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QSpinBox, QSlider, QFileDialog, QRadioButton, QButtonGroup, QScrollArea, QListWidget, QInputDialog,
    QTabWidget, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import colors as mcolors
import scipy
import scipy.stats as stats
from scipy.stats import zscore
import sys
import os
sys.setrecursionlimit(5000)
class RangeSlider(QWidget):
    valueChanged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.first_position = 0
        self.second_position = 100

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.first_slider = QSlider(Qt.Horizontal)
        self.first_slider.setRange(0, 100)
        self.first_slider.setValue(0)

        self.second_slider = QSlider(Qt.Horizontal)
        self.second_slider.setRange(0, 100)
        self.second_slider.setValue(100)

        self.layout.addWidget(self.first_slider)
        self.layout.addWidget(self.second_slider)

        self.first_slider.valueChanged.connect(self.on_first_slider_value_changed)
        self.second_slider.valueChanged.connect(self.on_second_slider_value_changed)

    def on_first_slider_value_changed(self, value):
        if value > self.second_slider.value():
            self.first_slider.setValue(self.second_slider.value())
            return
        self.first_position = value
        self.valueChanged.emit(self.first_position, self.second_position)

    def on_second_slider_value_changed(self, value):
        if value < self.first_slider.value():
            self.second_slider.setValue(self.first_slider.value())
            return
        self.second_position = value
        self.valueChanged.emit(self.first_position, self.second_position)

    def setRange(self, start, end):
        self.first_slider.setRange(start, end)
        self.second_slider.setRange(start, end)

    def setStart(self, value):
        self.first_slider.setValue(value)

    def setEnd(self, value):
        self.second_slider.setValue(value)


class ReactionTimeAnalysisGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Add these lines to initialize data-related attributes
        self.data = None
        self.original_data = None
        
        self.initUI()
        self.figure_data = {}
        self.current_figure_type = None
        self.excluded_participants = {}  # Change to dict to track per dataset
        self.excluded_trials = {}  # Add to track excluded trials per dataset
        self.datasets = {}  # Dictionary to store multiple datasets {name: {"data": DataFrame, "color": str}}
        self.dataset_colors = {}  # Store colors for each dataset
        self.dataset_patterns = {}  # Add this line to store patterns for datasets
        self.modality_colors = {
            'Audio': 'red',
            'Visual': 'blue',
            'Audiovisual': 'purple'
        }

    def initUI(self):
        self.setWindowTitle("SRT Analysis GUI")
        self.setGeometry(100, 100, 1300, 600)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Create a horizontal layout for the main widget
        main_layout = QHBoxLayout(self.main_widget)

        # Create a widget for the left side (controls)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Add dataset management controls to top of left side
        dataset_controls = QWidget()
        dataset_layout = QVBoxLayout(dataset_controls)
        
        # Dataset list
        self.dataset_list = QListWidget()
        self.dataset_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enables Ctrl/Cmd-click for multiple selections
        self.dataset_list.setMinimumHeight(100)  # Optional: ensure list is tall enough to show multiple items
        self.dataset_list.itemSelectionChanged.connect(self.on_dataset_selection_changed)
        
        # Dataset buttons
        dataset_buttons = QHBoxLayout()
        self.load_dataset_button = QPushButton('Load Dataset', self)
        self.load_dataset_button.clicked.connect(self.load_dataset)
        self.remove_dataset_button = QPushButton('Remove Dataset', self)
        self.remove_dataset_button.clicked.connect(self.remove_dataset)
        self.combine_datasets_button = QPushButton('Combine Datasets', self) # New button
        self.combine_datasets_button.clicked.connect(self.combine_datasets) # New connection
        self.format_csv_button = QPushButton('Format CSV', self)
        self.format_csv_button.clicked.connect(self.open_csv_for_formatting)
        
        dataset_buttons.addWidget(self.load_dataset_button)
        dataset_buttons.addWidget(self.remove_dataset_button)
        dataset_buttons.addWidget(self.combine_datasets_button) # Add to layout
        dataset_buttons.addWidget(self.format_csv_button)

        
        dataset_layout.addWidget(QLabel("Loaded Datasets:"))
        dataset_layout.addWidget(self.dataset_list)
        dataset_layout.addLayout(dataset_buttons)
        
        left_layout.insertWidget(0, dataset_controls)

        # Participant Selector
        self.participant_selector = QComboBox(self)
        self.participant_selector.currentIndexChanged.connect(self.update_participant_settings)
        left_layout.addWidget(self.participant_selector)

        # Add Exclude Participants Button
        self.exclude_participants_button = QPushButton('Exclude Participants', self)
        self.exclude_participants_button.clicked.connect(self.open_participant_selection_dialog)
        left_layout.addWidget(self.exclude_participants_button)
        self.exclude_participants_button.setVisible(False)

        # Create horizontal layout for exclusion buttons
        exclusion_buttons_layout = QHBoxLayout()
        
        # Exclude Trials Button
        self.exclude_trials_button = QPushButton('Exclude Trials', self)
        self.exclude_trials_button.clicked.connect(self.exclude_trials_dialog)
        exclusion_buttons_layout.addWidget(self.exclude_trials_button)
        
        # Undo Exclusions Button
        self.undo_exclusions_button = QPushButton('Undo All Exclusions', self)
        self.undo_exclusions_button.clicked.connect(self.undo_exclusions)
        self.undo_exclusions_button.setEnabled(False)  # Initially disabled
        exclusion_buttons_layout.addWidget(self.undo_exclusions_button)
        
        left_layout.addLayout(exclusion_buttons_layout)
        self.exclude_trials_button.setVisible(False)
        self.undo_exclusions_button.setVisible(False)

             # Statistical Test Toggle
        self.test_group = QButtonGroup(self)
        self.ttest_radio = QRadioButton("T-Test", self)
        self.bayes_radio = QRadioButton("Bayes Factor", self)
        self.test_group.addButton(self.ttest_radio)
        self.test_group.addButton(self.bayes_radio)
        self.ttest_radio.setChecked(True)
        
        # Create single horizontal layout for all stats controls
        stats_controls_layout = QHBoxLayout()
        
        # Add radio buttons with label
        stats_controls_layout.addWidget(QLabel("Statistical Test:"))
        stats_controls_layout.addWidget(self.ttest_radio)
        stats_controls_layout.addWidget(self.bayes_radio)
        
        # Add some spacing between radio buttons and checkboxes
        stats_controls_layout.addSpacing(20)
        
        # Add vertical line separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        stats_controls_layout.addWidget(separator)
        
        # Add some spacing after separator
        stats_controls_layout.addSpacing(20)
        
        # Add checkboxes
        self.between_stats_checkbox = QCheckBox("Between-Dataset Stats", self)
        self.within_stats_checkbox = QCheckBox("Within-Dataset Stats", self)
        self.between_stats_checkbox.setChecked(True)
        self.within_stats_checkbox.setChecked(False)
        stats_controls_layout.addWidget(self.between_stats_checkbox)
        stats_controls_layout.addWidget(self.within_stats_checkbox)
        
        # Add the combined layout to main layout
        left_layout.addLayout(stats_controls_layout)

        # Create horizontal layout for plot buttons
        plot_buttons_layout = QHBoxLayout()
        
        # Plot RT Buttons group
        self.plot_mean_button = QPushButton('Mean RTs', self)
        self.plot_mean_button.clicked.connect(self.plot_mean_rts)
        self.plot_median_button = QPushButton('Median RTs', self)
        self.plot_median_button.clicked.connect(self.plot_median_rts)
        self.plot_boxplot_button = QPushButton('Boxplot RTs', self)
        self.plot_boxplot_button.clicked.connect(self.plot_boxplot_rts)
        
        # Add buttons to horizontal layout
        plot_buttons_layout.addWidget(self.plot_mean_button)
        plot_buttons_layout.addWidget(self.plot_median_button)
        plot_buttons_layout.addWidget(self.plot_boxplot_button)
        
        # Add horizontal layout to main left layout
        left_layout.addLayout(plot_buttons_layout)

        # Y-axis Inputs
        yaxis_layout = QHBoxLayout()
        ymin_label = QLabel('Y-axis Min:')
        self.ymin_input = QLineEdit(self)
        self.ymin_input.setFixedWidth(50)
        self.ymin_input.setText('0')
        ymax_label = QLabel('Y-axis Max:')
        self.ymax_input = QLineEdit(self)
        self.ymax_input.setFixedWidth(50)
        self.ymax_input.setText('1000')

        yaxis_layout.addWidget(ymin_label)
        yaxis_layout.addWidget(self.ymin_input)
        yaxis_layout.addWidget(ymax_label)
        yaxis_layout.addWidget(self.ymax_input)

        left_layout.addLayout(yaxis_layout)

        self.plot_distribution_button = QPushButton('Plot Participant Distribution', self)
        self.plot_distribution_button.clicked.connect(self.plot_participant_distribution)
        left_layout.addWidget(self.plot_distribution_button)

        # ANOVA Button
        self.anova_button = QPushButton('Perform ANOVA', self)
        self.anova_button.clicked.connect(self.perform_anova_analysis)
        left_layout.addWidget(self.anova_button)

        # Race Model Selector and Parameters
        self.model_selector = QComboBox(self)
        self.model_selector.addItems(["Standard Race Model", "Coactivation Model",
                                      "Parallel Interactive Race Model",
                                      "Multisensory Response Enhancement Model"])
        self.model_selector.currentIndexChanged.connect(self.update_model_settings)
        left_layout.addWidget(self.model_selector)

        # Create widgets for model parameters
        self.create_model_parameter_widgets()
        left_layout.addWidget(self.coactivation_widget)
        left_layout.addWidget(self.pir_widget)
        left_layout.addWidget(self.mre_widget)

        self.more_info_button = QPushButton('Race Model Selection More Info', self)
        self.more_info_button.clicked.connect(self.show_more_info)
        left_layout.addWidget(self.more_info_button)

        # Add button next to plot race model button
        race_model_layout = QHBoxLayout()
        self.plot_race_model_button = QPushButton('Plot Race Model', self)
        self.plot_race_model_button.clicked.connect(self.plot_race_model)
        self.plot_violations_button = QPushButton('Plot Violations', self)
        self.plot_violations_button.clicked.connect(self.plot_race_violations)
        self.use_percentiles_checkbox = QCheckBox('Use Percentiles', self)
        race_model_layout.addWidget(self.plot_race_model_button)
        race_model_layout.addWidget(self.plot_violations_button)
        race_model_layout.addWidget(self.use_percentiles_checkbox)
        left_layout.addLayout(race_model_layout)

        # Scatter Plot Controls
        scatter_layout = QHBoxLayout()
        self.factor1_selector = QComboBox(self)
        self.factor2_selector = QComboBox(self)
        base_factors = ['Age', 'Interquartile Range (Total)', 'Interquartile Range (Audio)',
                        'Interquartile Range (Visual)', 'Interquartile Range (Audiovisual)',
                        'Race Violations', 'Total Trials', 'Mean RT (Audio)', 'Mean RT (Visual)',
                        'Mean RT (Audiovisual)','Median RT (Audio)','Median RT (Visual)','Median RT (Audiovisual)',
                        'Custom Column...']  # Added this line

        for selector in [self.factor1_selector, self.factor2_selector]:
            selector.clear()
            selector.addItems(base_factors)
            selector.currentTextChanged.connect(self.update_slider_visibility)
            selector.currentTextChanged.connect(self.handle_custom_factor_selection)  # New line to handle custom factor


        scatter_layout.addWidget(QLabel("Factor 1:"))
        scatter_layout.addWidget(self.factor1_selector)
        scatter_layout.addWidget(QLabel("Factor 2:"))
        scatter_layout.addWidget(self.factor2_selector)
        left_layout.addLayout(scatter_layout)

        # Add legend toggle checkbox
        self.show_legend_checkbox = QCheckBox('Show Legend', self)
        self.show_legend_checkbox.setChecked(True)
        left_layout.addWidget(self.show_legend_checkbox)

        # Percentile Range Slider
        self.percentile_range_slider = RangeSlider(self)
        self.percentile_range_slider.setRange(0, 100)
        self.percentile_range_slider.setStart(0)
        self.percentile_range_slider.setEnd(100)
        # Create the label before using it
        self.percentile_range_slider_label = QLabel('Include Trials Within CDF Range: 0% - 100%\n(trials outside range will be excluded)', self)
        self.percentile_range_slider_label.setWordWrap(True)  # Allow text wrapping
        self.percentile_range_slider.valueChanged.connect(self.update_percentile_range_label)
        
        left_layout.addWidget(self.percentile_range_slider_label)
        left_layout.addWidget(self.percentile_range_slider)

        scatter_button_layout = QHBoxLayout()
        self.plot_scatter_button = QPushButton('Scatter Plot', self)
        self.plot_scatter_button.clicked.connect(self.plot_scatter)
        self.sync_axes_checkbox = QCheckBox('Sync Axes', self)
        scatter_button_layout.addWidget(self.plot_scatter_button)
        scatter_button_layout.addWidget(self.sync_axes_checkbox)
        left_layout.addLayout(scatter_button_layout)

        # Add a stretch to push everything to the top
        left_layout.addStretch()

        # Create a widget for the right side (figure and explanation)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.figure = plt.figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)

        self.save_figure_button = QPushButton('Save Figure', self)
        self.save_figure_button.clicked.connect(self.save_figure)
        right_layout.addWidget(self.save_figure_button)

        self.explanation_label = QLabel('', self)
        right_layout.addWidget(self.explanation_label)

        self.anova_table = QTableWidget()
        self.anova_table.setVisible(False)
        right_layout.addWidget(self.anova_table)

        self.save_figure_data_button = QPushButton('Save Figure Data', self)
        self.save_figure_data_button.clicked.connect(self.save_figure_data)
        right_layout.addWidget(self.save_figure_data_button)

        self.outlier_report = QTextEdit(self)
        self.outlier_report.setReadOnly(True)
        self.outlier_report.setMaximumHeight(100)  # Limit the height
        self.outlier_report.setVisible(False)
        right_layout.addWidget(self.outlier_report)  # Add to right layout after the canvas

        # Add the left and right widgets to the main layout
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)

        self.show()

    def create_model_parameter_widgets(self):
        # Coactivation Model parameters
        self.coactivation_widget = QWidget(self)
        coactivation_main_layout = QVBoxLayout(self.coactivation_widget)
        coactivation_main_layout.setSpacing(5)  # Reduce spacing
        
        # Create horizontal layout for coactivation parameters
        coactivation_params_layout = QHBoxLayout()
        
        # Mean parameter
        mean_layout = QVBoxLayout()
        self.coactivation_mean_slider, mean_label = self.create_labeled_slider(0, 1000, "Mean μ_c (avg RT)", "(ms)")
        mean_layout.addWidget(mean_label)
        
        # Std Dev parameter
        std_layout = QVBoxLayout()
        self.coactivation_std_slider, std_label = self.create_labeled_slider(1, 500, "Std σ_c (RT variability)", "(ms)")
        std_layout.addWidget(std_label)
        
        coactivation_params_layout.addLayout(mean_layout)
        coactivation_params_layout.addLayout(std_layout)
        coactivation_main_layout.addLayout(coactivation_params_layout)
    
        # Parallel Interactive Race Model parameters
        self.pir_widget = QWidget(self)
        pir_layout = QVBoxLayout(self.pir_widget)
        pir_layout.setSpacing(5)
        self.pir_interaction_slider, interact_label = self.create_labeled_slider(0, 100, "Interaction γ (cross-modal strength)", "%")
        pir_layout.addWidget(interact_label)
    
        # MRE Model parameters
        self.mre_widget = QWidget(self)
        mre_main_layout = QVBoxLayout(self.mre_widget)
        mre_main_layout.setSpacing(5)
        
        # Create two rows of parameters
        mre_top_row = QHBoxLayout()
        mre_bottom_row = QHBoxLayout()
        
        # Alpha and Beta in top row
        alpha_layout = QVBoxLayout()
        self.mre_alpha_slider, alpha_label = self.create_labeled_slider(0, 100, "α (auditory weight)", "%")
        alpha_layout.addWidget(alpha_label)
        
        beta_layout = QVBoxLayout()
        self.mre_beta_slider, beta_label = self.create_labeled_slider(0, 100, "β (visual weight)", "%")
        beta_layout.addWidget(beta_label)
        
        mre_top_row.addLayout(alpha_layout)
        mre_top_row.addLayout(beta_layout)
        
        # Lambda in bottom row (fix the incorrect method call)
        lambda_layout = QVBoxLayout()
        self.mre_lambda_slider, lambda_label = self.create_labeled_slider(0, 100, "λ (integration strength)", "%")
        lambda_layout.addWidget(lambda_label)
        mre_bottom_row.addLayout(lambda_layout)  # Changed from addLayout(lambda_label)
        
        mre_main_layout.addLayout(mre_top_row)
        mre_main_layout.addLayout(mre_bottom_row)
    
        # Initially hide all parameter widgets
        self.coactivation_widget.setVisible(False)
        self.pir_widget.setVisible(False)
        self.mre_widget.setVisible(False)
    
    def create_labeled_slider(self, min_value, max_value, name, description):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(2)  # Reduce vertical spacing
        
        # Create label row
        label_row = QHBoxLayout()
        name_label = QLabel(f"{name}")
        value_label = QLabel(f"{(min_value + max_value) // 2}")
        label_row.addWidget(name_label)
        label_row.addWidget(value_label)
        
        # Create and setup slider
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue((min_value + max_value) // 2)
        slider.valueChanged.connect(lambda v: value_label.setText(f"{v}"))
        
        # Add description if provided
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: gray; font-size: 8pt;")
            layout.addWidget(desc_label)
        
        layout.addLayout(label_row)
        layout.addWidget(slider)
        
        return slider, container
    def update_model_settings(self):
        selected_model = self.model_selector.currentText()
        self.coactivation_widget.setVisible(selected_model == "Coactivation Model")
        self.pir_widget.setVisible(selected_model == "Parallel Interactive Race Model")
        self.mre_widget.setVisible(selected_model == "Multisensory Response Enhancement Model")

    def update_participant_settings(self):
        participant = self.participant_selector.currentText()
        self.exclude_participants_button.setVisible(participant == "All Participants")
        self.exclude_trials_button.setVisible(True)
        self.undo_exclusions_button.setVisible(True)


    def exclude_trials_dialog(self):
        """Opens a dialog for excluding trials based on various criteria"""
        # Check if any dataset is selected
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Dataset Selected", 
                              "Please select a dataset before attempting to exclude trials.")
            return
        
        # Get the selected dataset
        dataset_name = selected_items[0].text()
        if dataset_name not in self.datasets:
            QMessageBox.warning(self, "Dataset Error", 
                              "Selected dataset not found.")
            return
            
        # Work with the selected dataset's data
        current_data = self.datasets[dataset_name]["data"].copy()
    
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Exclude Trials - {dataset_name}")
        dialog.setGeometry(100, 100, 400, 300)
        dialog_layout = QVBoxLayout(dialog)
    
        # Create exclusion criteria widgets
        criteria_group = QWidget()
        criteria_layout = QFormLayout(criteria_group)
    
        # RT Range criteria
        rt_min_input = QLineEdit()
        rt_min_input.setPlaceholderText("e.g., 100")
        rt_max_input = QLineEdit()
        rt_max_input.setPlaceholderText("e.g., 1000")
        
        rt_range_layout = QHBoxLayout()
        rt_range_layout.addWidget(QLabel("Min:"))
        rt_range_layout.addWidget(rt_min_input)
        rt_range_layout.addWidget(QLabel("Max:"))
        rt_range_layout.addWidget(rt_max_input)
        
        criteria_layout.addRow("Exclude Outside RT Range (ms):", rt_range_layout)
    
        # Z-score threshold
        zscore_input = QLineEdit()
        zscore_input.setPlaceholderText("e.g., 2.5")
        criteria_layout.addRow("Z-score threshold:", zscore_input)
    
        # Percentage from median
        percent_input = QLineEdit()
        percent_input.setPlaceholderText("e.g., 50")
        criteria_layout.addRow("% deviation from median:", percent_input)
    
        dialog_layout.addWidget(criteria_group)
    
        # Add checkboxes for modalities
        modality_group = QWidget()
        modality_layout = QHBoxLayout(modality_group)
        audio_check = QCheckBox("Audio")
        visual_check = QCheckBox("Visual")
        av_check = QCheckBox("Audiovisual")
        audio_check.setChecked(True)
        visual_check.setChecked(True)
        av_check.setChecked(True)
        
        modality_layout.addWidget(QLabel("Apply to modalities:"))
        modality_layout.addWidget(audio_check)
        modality_layout.addWidget(visual_check)
        modality_layout.addWidget(av_check)
        
        dialog_layout.addWidget(modality_group)
    
        # Preview button
        preview_button = QPushButton("Preview Exclusions")
        dialog_layout.addWidget(preview_button)
    
        # Results text area
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        dialog_layout.addWidget(results_text)
    
        # Button box
        button_box = QHBoxLayout()
        apply_button = QPushButton("Apply Exclusions")
        close_button = QPushButton("Close")
        button_box.addWidget(apply_button)
        button_box.addWidget(close_button)
        dialog_layout.addLayout(button_box)
    
        def preview_exclusions():
            trials_to_exclude = self.find_trials_to_exclude(
                rt_min_input.text(),
                rt_max_input.text(),
                zscore_input.text(),
                percent_input.text(),
                [audio_check.isChecked(), visual_check.isChecked(), av_check.isChecked()],
                current_data
            )
            
            summary = "Preview of trials to be excluded:\n\n"
            total_excluded = 0
            
            for participant, exclusions in trials_to_exclude.items():
                if exclusions:
                    n_excluded = len(exclusions)
                    total_excluded += n_excluded
                    participant_data = current_data[current_data['participant_number'] == participant]
                    total_trials = len(participant_data)
                    summary += f"Participant {participant}: {n_excluded} of {total_trials} trials "
                    summary += f"({(n_excluded/total_trials*100):.1f}%)\n"
            
            summary += f"\nTotal trials to be excluded: {total_excluded}"
            results_text.setText(summary)
            
            apply_button.setEnabled(total_excluded > 0)
    
        def apply_exclusions():
            trials_to_exclude = self.find_trials_to_exclude(
                rt_min_input.text(),
                rt_max_input.text(),
                zscore_input.text(),
                percent_input.text(),
                [audio_check.isChecked(), visual_check.isChecked(), av_check.isChecked()],
                current_data
            )
            
            all_indices = []
            for participant_indices in trials_to_exclude.values():
                all_indices.extend(participant_indices)
            
            if all_indices:
                if dataset_name not in self.excluded_trials:
                    self.excluded_trials[dataset_name] = []
                self.excluded_trials[dataset_name].extend(all_indices)
    
                updated_data = current_data.drop(all_indices).reset_index(drop=True)
                self.datasets[dataset_name]["data"] = updated_data
    
                QMessageBox.information(dialog, "Success", 
                                    f"Successfully excluded {len(all_indices)} trials from {dataset_name}")
                self.undo_exclusions_button.setEnabled(True)
                dialog.close()
                
                self.update_plots()
    
        preview_button.clicked.connect(preview_exclusions)
        apply_button.clicked.connect(apply_exclusions)
        close_button.clicked.connect(dialog.close)
        
        apply_button.setEnabled(False)
        
        dialog.exec_()
    

    def update_model_settings(self):
        selected_model = self.model_selector.currentText()
        self.coactivation_widget.setVisible(selected_model == "Coactivation Model")
        self.pir_widget.setVisible(selected_model == "Parallel Interactive Race Model")
        self.mre_widget.setVisible(selected_model == "Multisensory Response Enhancement Model")

    def update_participant_settings(self):
        participant = self.participant_selector.currentText()
        self.exclude_participants_button.setVisible(participant == "All Participants")
        self.exclude_trials_button.setVisible(True)
        self.undo_exclusions_button.setVisible(True)


    def handle_outlier_exclusion(self, *args):
        if self.exclude_outliers_checkbox.isChecked():
            if not hasattr(self, 'original_data'):
                self.original_data = self.data.copy()
            try:
                z_score_threshold = float(self.zscore_threshold_input.text())
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", 
                                "Please enter a valid number for z-score threshold.")
                self.exclude_outliers_checkbox.setChecked(False)
                return
            
            # Restore original data before applying new threshold
            self.data = self.original_data.copy()
            self.exclude_outliers(z_score_threshold)
            
            # Refresh current plot if one exists
            if hasattr(self, 'current_figure_type'):
                if self.current_figure_type == 'mean_rts':
                    self.plot_mean_rts()
                elif self.current_figure_type == 'median_rts':
                    self.plot_median_rts()
                elif self.current_figure_type == 'boxplot_rts':
                    self.plot_boxplot_rts()
                elif self.current_figure_type == 'participant_distribution':
                    self.plot_participant_distribution()
                elif self.current_figure_type == 'race_model':
                    self.plot_race_model()
                elif self.current_figure_type == 'scatter':
                    self.plot_scatter()
        else:
            if hasattr(self, 'original_data'):
                self.data = self.original_data.copy()
                self.outlier_report.setVisible(False)
                self.outlier_report.clear()
                # Refresh current plot
                if hasattr(self, 'current_figure_type'):
                    getattr(self, f'plot_{self.current_figure_type}')()

    def exclude_outliers(self, z_score_threshold):
        total_excluded = 0
        participant_outliers = {}
        
        if self.participant_selector.currentText() == "All Participants":
            excluded_participants = self.get_excluded_participants()
            participants = [p for p in self.data['participant_number'].unique() 
                        if str(p) not in excluded_participants]
        else:
            participant_number = self.participant_selector.currentText().split()[-1]
            participants = [participant_number]
        
        for participant in participants:
            participant_data = self.data[self.data['participant_number'] == participant]
            outlier_indices = []
            modality_outliers = {}
            
            for modality in [1, 2, 3]:  # Audio, Visual, Audiovisual
                modality_data = participant_data[participant_data['modality'] == modality]
                z_scores = np.abs(scipy.stats.zscore(modality_data['reaction_time']))
                modality_outliers[modality] = len(z_scores[z_scores >= z_score_threshold])
                outlier_indices.extend(modality_data.index[z_scores >= z_score_threshold].tolist())
            
            if outlier_indices:
                participant_outliers[participant] = {
                    'total': len(outlier_indices),
                    'audio': modality_outliers[1],
                    'visual': modality_outliers[2],
                    'audiovisual': modality_outliers[3]
                }
                total_excluded += len(outlier_indices)
                self.data = self.data.drop(outlier_indices).reset_index(drop=True)
        
        # Create detailed message about outlier removal
        message = "Outlier Removal Summary:\n"
        message += f"Criteria: Trials with |z-score| > {z_score_threshold} within each modality\n\n"
        
        if participant_outliers:
            for participant, stats in participant_outliers.items():
                message += f"Participant {participant}:\n"
                message += f"- Audio: {stats['audio']} trials\n"
                message += f"- Visual: {stats['visual']} trials\n"
                message += f"- Audiovisual: {stats['audiovisual']} trials\n"
                message += f"- Total: {stats['total']} trials\n\n"
            message += f"Total trials removed across all participants: {total_excluded}"
        else:
            message = "No outliers were detected using the current criteria."
        
        # Update the outlier report
        self.outlier_report.setVisible(True)
        self.outlier_report.setText(message)
        
        # Show a small notification
        self.statusBar().showMessage(f"Excluded {total_excluded} outlier trials", 5000)

    def find_trials_to_exclude(self, rt_min, rt_max, zscore_thresh, percent_deviation, 
                              modalities_enabled, data):
        """
        Find trials to exclude based on given criteria.
        
        Parameters:
        -----------
        rt_min : str
            Minimum reaction time threshold
        rt_max : str
            Maximum reaction time threshold
        zscore_thresh : str
            Z-score threshold for outlier detection
        percent_deviation : str
            Percentage deviation from median threshold
        modalities_enabled : list
            List of boolean flags for each modality [audio, visual, audiovisual]
        data : pandas.DataFrame
            Dataset to analyze
        
        Returns:
        --------
        dict
            Dictionary mapping participant numbers to lists of trial indices to exclude
        """
        if data is None:
            QMessageBox.warning(None, "No Data", 
                              "Please load data before attempting to exclude trials.")
            return {}
    
        trials_to_exclude = {}
        
        # Get current participant or all participants
        if self.participant_selector.currentText() == "All Participants":
            participants = data['participant_number'].unique()
        else:
            participant_str = self.participant_selector.currentText().split()[-1]
            participants = [int(participant_str)]
        
        # Convert inputs to numeric values, using None if empty
        try:
            rt_min = float(rt_min) if rt_min else None
            rt_max = float(rt_max) if rt_max else None
            zscore_thresh = float(zscore_thresh) if zscore_thresh else None
            percent_dev = float(percent_deviation) if percent_deviation else None
        except ValueError:
            QMessageBox.warning(None, "Invalid Input", 
                            "Please enter valid numbers for the criteria.")
            return {}
    
        # Create list of modalities to check based on checkboxes
        modality_map = {0: 1, 1: 2, 2: 3}  # Maps checkbox index to modality value
        selected_modalities = [modality_map[i] for i, enabled in enumerate(modalities_enabled) if enabled]
        
        if not selected_modalities:
            QMessageBox.warning(None, "No Modalities", 
                            "Please select at least one modality.")
            return {}
    
        for participant in participants:
            participant_data = data[data['participant_number'] == participant]
            exclusion_indices = []
            
            for modality in selected_modalities:
                modality_data = participant_data[participant_data['modality'] == modality]
                
                if len(modality_data) == 0:
                    continue
                
                # RT range criteria
                if rt_min is not None:
                    exclusion_indices.extend(
                        modality_data[modality_data['reaction_time'] < rt_min].index.tolist())
                if rt_max is not None:
                    exclusion_indices.extend(
                        modality_data[modality_data['reaction_time'] > rt_max].index.tolist())
                
                # Z-score criteria
                if zscore_thresh is not None and len(modality_data) > 1:
                    z_scores = np.abs(stats.zscore(modality_data['reaction_time']))
                    exclusion_indices.extend(
                        modality_data[z_scores > zscore_thresh].index.tolist())
                
                # Percentage deviation from median criteria
                if percent_dev is not None:
                    median_rt = modality_data['reaction_time'].median()
                    deviation = np.abs(modality_data['reaction_time'] - median_rt) / median_rt * 100
                    exclusion_indices.extend(
                        modality_data[deviation > percent_dev].index.tolist())
            
            # Store unique indices for this participant
            if exclusion_indices:
                trials_to_exclude[participant] = list(set(exclusion_indices))
        
        return trials_to_exclude

    def load_data(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            self.original_data = pd.read_csv(file_path)  # Store original data
            self.data = self.original_data.copy()

            # Exclude participants with incomplete modality data
            participants_to_exclude = []
            for participant in self.data['participant_number'].unique():
                participant_data = self.data[self.data['participant_number'] == participant]
                if len(participant_data['modality'].unique()) < 3:
                    participants_to_exclude.append(participant)

            # Filter out excluded participants
            if participants_to_exclude:
                self.data = self.data[~self.data['participant_number'].isin(participants_to_exclude)]
                print(f"Participants excluded due to incomplete modality data: {', '.join(map(str, participants_to_exclude))}")
            else:
                print("No participants were excluded due to incomplete modality data.")

            # Update participant selector after filtering
            self.statusBar().showMessage('Data loaded successfully!', 5000)
            self.participant_selector.clear()
            self.participant_selector.addItem("All Participants")
            participants = self.data['participant_number'].unique()
            for participant in participants:
                self.participant_selector.addItem(f"Participant {participant}")
            self.excluded_participants = []  # Reset excluded participants when new data is loaded

    def get_filtered_data(self, dataset_name=None):
        """Get filtered data based on current selection and exclusions"""
        try:
            if dataset_name and dataset_name in self.datasets:
                data = self.datasets[dataset_name]["data"].copy()
                
                # Apply participant exclusions
                if dataset_name in self.excluded_participants:
                    excluded_parts = self.excluded_participants[dataset_name]
                    data = data[~data['participant_number'].isin(excluded_parts)]
                
                # Apply trial exclusions
                if dataset_name in self.excluded_trials:
                    excluded_trials = self.excluded_trials[dataset_name]
                    valid_indices = [idx for idx in excluded_trials if idx in data.index]
                    if valid_indices:
                        data = data.drop(valid_indices)
                    data = data.reset_index(drop=True)
                
                # Apply participant filter
                if self.participant_selector.currentText() != "All Participants":
                    participant_number = int(self.participant_selector.currentText().split()[-1])
                    data = data[data['participant_number'] == participant_number]
                
                return data
                
            # Return data for first selected dataset if no specific dataset provided
            selected_items = self.dataset_list.selectedItems()
            if selected_items:
                return self.get_filtered_data(selected_items[0].text())
            
            return None
            
        except Exception as e:
            print(f"Error in get_filtered_data: {str(e)}")
            return None

    def remove_dataset(self):
        selected_items = self.dataset_list.selectedItems()
        if selected_items:
            for item in selected_items:
                name = item.text()
                del self.datasets[name]
                if name in self.excluded_participants:
                    del self.excluded_participants[name]
                if name in self.excluded_trials:
                    del self.excluded_trials[name]
                if name in self.dataset_colors:
                    del self.dataset_colors[name]
                self.dataset_list.takeItem(self.dataset_list.row(item))
            
            self.update_participant_selector()

    def on_dataset_selection_changed(self):
        """Handle when dataset selection changes"""
        selected_items = self.dataset_list.selectedItems()
        self.remove_dataset_button.setEnabled(len(selected_items) > 0)
        
        # Enable/disable plotting buttons based on selection
        has_selection = len(selected_items) > 0
        for button in [self.plot_mean_button, self.plot_median_button, 
                      self.plot_boxplot_button, self.plot_distribution_button,
                      self.plot_race_model_button, self.plot_violations_button,
                      self.plot_scatter_button]:
            button.setEnabled(has_selection)
        
        # Update participant selector
        self.update_participant_selector()
        
        # Update any current plots if they exist
        if hasattr(self, 'current_figure_type') and self.current_figure_type:
            self.update_plots()

    def update_participant_selector(self):
        """Update participant selector based on selected datasets"""
        self.participant_selector.clear()
        self.participant_selector.addItem("All Participants")
        
        selected_items = self.dataset_list.selectedItems()
        if selected_items:
            all_participants = set()
            for item in selected_items:
                data = self.datasets[item.text()]["data"]
                all_participants.update(data['participant_number'].unique())
            
            for participant in sorted(all_participants):
                self.participant_selector.addItem(f"Participant {participant}")

    def calculate_mean_rt(self, data):
        mean_rt = data.groupby('modality')['reaction_time'].mean()
        std_error = data.groupby('modality')['reaction_time'].sem()
        return mean_rt, std_error

    def calculate_median_rt(self, data):
        median_rt = data.groupby('modality')['reaction_time'].median()
        std_error = data.groupby('modality')['reaction_time'].apply(stats.sem)
        return median_rt, std_error

    def draw_significance_brackets(self, ax, x1, x2, y, p_value=None, bf10=None, 
                                 is_between_datasets=False, bracket_level=0):
        """Draw significance brackets with statistics"""
        bar_width = 0.8 / len(self.dataset_list.selectedItems())
        base_gap = bar_width * 0.15  # Reduced from 0.2
        
        # Adjust height based on bracket level with tighter spacing
        if is_between_datasets:
            # Between-dataset brackets go higher with larger gaps
            level_height = base_gap * 1.2  # Reduced from 1.5
            bar_height = y + (bracket_level * level_height)
            line_width = 1.5
            gap = base_gap * 1.2  # Reduced from 1.5
        else:
            # Within-dataset brackets with tighter spacing
            level_height = base_gap * 0.8  # Reduced from 1.5
            bar_height = y + (bracket_level * level_height)
            line_width = 1.0
            gap = base_gap
        
        # Calculate center positions for bars with tighter spacing
        x1_center = x1 + (bar_width/2)
        x2_center = x2 + (bar_width/2)
        
        # Draw the main bracket
        ax.plot([x1_center, x1_center, x2_center, x2_center], 
                [bar_height, bar_height + gap, bar_height + gap, bar_height], 
                'k-', linewidth=line_width)
        
        # Add smaller "feet" - reduced from 0.3
        foot_length = gap * 0.2
        ax.plot([x1_center, x1_center], [bar_height, bar_height - foot_length], 
                'k-', linewidth=line_width)
        ax.plot([x2_center, x2_center], [bar_height, bar_height - foot_length], 
                'k-', linewidth=line_width)
        
        # Center text with reduced gap
        center = (x1_center + x2_center) / 2
        if bf10 is not None:
            if bf10 > 1000:
                stats_text = f"BF₁₀={bf10:.2e}"
            else:
                stats_text = f"BF₁₀={bf10:.2f}"
        else:
            if p_value < 0.001:
                stats_text = '***'
            elif p_value < 0.01:
                stats_text = '**' 
            elif p_value < 0.05:
                stats_text = '*'
            else:
                stats_text = 'ns'
        
        # Position text closer to bracket
        ax.text(center, bar_height + gap * 1.1, stats_text,
                ha='center', va='bottom', fontsize=8)
        
    
    def get_modality_shade(self, base_color, dataset_index, n_datasets):
        """Get modality color shade based on dataset index"""
        # Make shade differences more dramatic
        shade_step = 0.4  # Increased from 0.2 for more contrast
        alpha = 1.0 - (dataset_index * shade_step)
        return self.adjust_lightness(base_color, alpha)


    def plot_mean_rts(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
    
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.current_figure_type = 'mean_rts'
    
        # Set up width and positions
        n_datasets = len(selected_items)
        n_conditions = 3
        total_width = 0.8
        bar_width = total_width / n_datasets
        group_positions = np.arange(n_conditions)
        
        # Calculate global max height first
        global_max_height = 0
        for item in selected_items:
            data = self.get_filtered_data(item.text())
            if data is not None:
                mean_rt, std_error = self.calculate_mean_rt(data)
                global_max_height = max(global_max_height, np.max(mean_rt + std_error))
    
        # Plot datasets and calculate statistics
        stats_text = "Within Dataset Comparisons:\n"
        for i, item in enumerate(selected_items):
            name = item.text()
            data = self.get_filtered_data(name)
            if data is None:
                continue
                
            mean_rt, std_error = self.calculate_mean_rt(data)
            x = group_positions + (i - (n_datasets-1)/2) * bar_width
            
            # Plot bars with different patterns
            for j, modality in enumerate(['Audio', 'Visual', 'Audiovisual']):
                base_color = self.modality_colors[modality]
                pattern = self.datasets[name]["pattern"]
                alpha = self.datasets[name]["alpha"]
                
                # Create bar with correct color and alpha
                bar = ax.bar(x[j], mean_rt.iloc[j], bar_width,  # Changed value to mean_rt.iloc[j]
                            yerr=std_error.iloc[j], 
                            label=f"{modality} ({name})",
                            color='none' if pattern == 'clear' else ('white' if pattern != 'solid' else base_color),
                            edgecolor=base_color,
                            alpha=alpha,
                            capsize=4)
            
                # Apply pattern after bar creation
                if pattern == 'hatched':
                    bar[0].set_hatch('///')
                elif pattern == 'dotted':
                    bar[0].set_hatch('...')
                elif pattern == 'dashed':
                    bar[0].set_hatch('--')
                elif pattern == 'cross-hatched':
                    bar[0].set_hatch('xxx')
    
            # Within-dataset comparisons
            if data is not None:
                stats_text += f"{name}: "
                comparisons = [(0,1), (1,2), (0,2)]
                pair_names = ["A v V", "V v AV", "A v AV"]
                
                for idx, (mod_pair, pair_name) in enumerate(zip(comparisons, pair_names)):
                    mod1, mod2 = mod_pair
                    rt1 = data[data['modality'] == mod1+1]['reaction_time']
                    rt2 = data[data['modality'] == mod2+1]['reaction_time']
                    
                    # Updated height calculations for better staggering
                    base_height = global_max_height * 1.05  # Starting height
                    dataset_offset = global_max_height * 0.20 * i  # Larger offset between datasets
                    comparison_spacing = global_max_height * 0.06  # Larger spacing between comparisons
                    bracket_height = base_height + dataset_offset + (idx * comparison_spacing)
                    
                    if self.ttest_radio.isChecked():
                        t_stat, p_val = ttest_ind(rt1, rt2)
                        stats_text += f"{pair_name} p={p_val:.2e}, "
                        if self.within_stats_checkbox.isChecked():
                            self.draw_significance_brackets(ax, x[mod1], x[mod2], 
                                                         bracket_height, 
                                                         p_value=p_val,
                                                         bracket_level=idx,
                                                         is_between_datasets=False)
                    else:
                        t_stat, _ = ttest_ind(rt1, rt2)
                        bf10 = bayesfactor_ttest(t=t_stat, nx=len(rt1), ny=len(rt2))
                        stats_text += f"{pair_name} BF₁₀={bf10:.2e}, "
                        if self.within_stats_checkbox.isChecked():
                            self.draw_significance_brackets(ax, x[mod1], x[mod2], 
                                                         bracket_height,
                                                         bf10=bf10,
                                                         bracket_level=idx,
                                                         is_between_datasets=False)
                stats_text = stats_text.rstrip(", ") + "\n"
    
        # Between-dataset comparisons
        if len(selected_items) > 1:
            stats_text += "\nBetween Datasets:\n"
            for modality, mod_name in enumerate(['Audio', 'Visual', 'Audiovisual'], 1):
                stats_text += f"{mod_name}: "
                between_comparisons = []
                
                for i, item1 in enumerate(selected_items[:-1]):
                    for j, item2 in enumerate(selected_items[i+1:], i+1):
                        data1 = self.get_filtered_data(item1.text())
                        data2 = self.get_filtered_data(item2.text())
                        if data1 is not None and data2 is not None:
                            rt1 = data1[data1['modality'] == modality]['reaction_time']
                            rt2 = data2[data2['modality'] == modality]['reaction_time']
                            if len(rt1) > 0 and len(rt2) > 0:
                                x1 = group_positions[modality-1] + (i - (n_datasets-1)/2) * bar_width
                                x2 = group_positions[modality-1] + (j - (n_datasets-1)/2) * bar_width
                                
                                bracket_height = global_max_height * (1.40 + 0.06 * (j-i))
                                
                                if self.ttest_radio.isChecked():
                                    t_stat, p_val = ttest_ind(rt1, rt2)
                                    stats_text += f"{item1.text()} v {item2.text()} p={p_val:.2e}, "
                                    if self.between_stats_checkbox.isChecked():
                                        self.draw_significance_brackets(ax, x1, x2,
                                                                     bracket_height,
                                                                     p_value=p_val,
                                                                     bracket_level=j-i,
                                                                     is_between_datasets=True)
                                else:
                                    t_stat, _ = ttest_ind(rt1, rt2)
                                    bf10 = bayesfactor_ttest(t=t_stat, nx=len(rt1), ny=len(rt2))
                                    stats_text += f"{item1.text()} v {item2.text()} BF₁₀={bf10:.2e}, "
                                    if self.between_stats_checkbox.isChecked():
                                        self.draw_significance_brackets(ax, x1, x2,
                                                                     bracket_height,
                                                                     bf10=bf10,
                                                                     bracket_level=j-i,
                                                                     is_between_datasets=True)
                stats_text = stats_text.rstrip(", ") + "\n"
    
        # Plot customization
        ax.set_xticks(group_positions)
        ax.set_xticklabels(['Audio', 'Visual', 'Audiovisual'])
        ax.set_xlabel('Modality')
        ax.set_ylabel('Reaction Time (ms)')
        ax.set_title('Mean Reaction Times by Dataset')
        
        if self.show_legend_checkbox.isChecked():
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            self.figure.subplots_adjust(right=0.85)

        figure_data = {
            'datasets': {}
        }
        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is not None:
                mean_rt, std_error = self.calculate_mean_rt(data)
                figure_data['datasets'][name] = {
                    'mean_rt': mean_rt.tolist(),
                    'std_error': std_error.tolist()
                }
        self.store_figure_data('mean_rts', figure_data)
        # Increase y-axis limit to accommodate all brackets
        self._set_y_limits(ax, 0, global_max_height * 1.5)
    
        self._customize_axes(ax)
        self.figure.tight_layout()
        self.canvas.draw()
        self.explanation_label.setText(stats_text)



    def plot_median_rts(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
    
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.current_figure_type = 'median_rts'
    
        # Set up width and positions
        n_datasets = len(selected_items)
        n_conditions = 3
        total_width = 0.8
        bar_width = total_width / n_datasets
        group_positions = np.arange(n_conditions)
        
        # Calculate global max height first
        global_max_height = 0
        for item in selected_items:
            data = self.get_filtered_data(item.text())
            if data is not None:
                median_rt, std_error = self.calculate_median_rt(data)
                global_max_height = max(global_max_height, np.max(median_rt + std_error))
    
        # Plot datasets and calculate statistics
        stats_text = "Within Dataset Comparisons:\n"
        for i, item in enumerate(selected_items):
            name = item.text()
            data = self.get_filtered_data(name)
            if data is None:
                continue
                
            median_rt, std_error = self.calculate_median_rt(data)
            x = group_positions + (i - (n_datasets-1)/2) * bar_width
            
            # Plot bars with different patterns
            for j, modality in enumerate(['Audio', 'Visual', 'Audiovisual']):
                base_color = self.modality_colors[modality]
                pattern = self.datasets[name]["pattern"]
                alpha = self.datasets[name]["alpha"]
                
                # Create bar with correct color and alpha
                bar = ax.bar(x[j], median_rt.iloc[j], bar_width,
                            yerr=std_error.iloc[j], 
                            label=f"{modality} ({name})",
                            color='none' if pattern == 'clear' else ('white' if pattern != 'solid' else base_color),
                            edgecolor=base_color,
                            alpha=alpha,
                            capsize=4)

                # Apply pattern after bar creation
                if pattern == 'hatched':
                    bar[0].set_hatch('///')
                elif pattern == 'dotted':
                    bar[0].set_hatch('...')
                elif pattern == 'dashed':
                    bar[0].set_hatch('--')
                elif pattern == 'cross-hatched':
                    bar[0].set_hatch('xxx')
    
            # Within-dataset comparisons
            if data is not None:
                stats_text += f"{name}: "
                comparisons = [(0,1), (1,2), (0,2)]
                pair_names = ["A v V", "V v AV", "A v AV"]
                
                for idx, (mod_pair, pair_name) in enumerate(zip(comparisons, pair_names)):
                    mod1, mod2 = mod_pair
                    rt1 = data[data['modality'] == mod1+1]['reaction_time']
                    rt2 = data[data['modality'] == mod2+1]['reaction_time']
                    
                    # Updated height calculations for better staggering
                    base_height = global_max_height * 1.05  # Starting height
                    dataset_offset = global_max_height * 0.20 * i  # Larger offset between datasets
                    comparison_spacing = global_max_height * 0.06  # Larger spacing between comparisons
                    bracket_height = base_height + dataset_offset + (idx * comparison_spacing)
                    
                    if self.ttest_radio.isChecked():
                        t_stat, p_val = ttest_ind(rt1, rt2)
                        stats_text += f"{pair_name} p={p_val:.2e}, "
                        if self.within_stats_checkbox.isChecked():
                            self.draw_significance_brackets(ax, x[mod1], x[mod2], 
                                                         bracket_height, 
                                                         p_value=p_val,
                                                         bracket_level=idx,
                                                         is_between_datasets=False)
                    else:
                        t_stat, _ = ttest_ind(rt1, rt2)
                        bf10 = bayesfactor_ttest(t=t_stat, nx=len(rt1), ny=len(rt2))
                        if abs(bf10) > 1000:
                            stats_text += f"{pair_name} BF₁₀={bf10:.2e}, "
                        else:
                            stats_text += f"{pair_name} BF₁₀={bf10:.2f}, "
                        if self.within_stats_checkbox.isChecked():
                            self.draw_significance_brackets(ax, x[mod1], x[mod2], 
                                                         bracket_height,
                                                         bf10=bf10,
                                                         bracket_level=idx,
                                                         is_between_datasets=False)
                stats_text = stats_text.rstrip(", ") + "\n"
    
        # Between-dataset comparisons
        if len(selected_items) > 1:
            stats_text += "\nBetween Datasets:\n"
            for modality, mod_name in enumerate(['Audio', 'Visual', 'Audiovisual'], 1):
                stats_text += f"{mod_name}: "
                between_comparisons = []
                
                for i, item1 in enumerate(selected_items[:-1]):
                    for j, item2 in enumerate(selected_items[i+1:], i+1):
                        data1 = self.get_filtered_data(item1.text())
                        data2 = self.get_filtered_data(item2.text())
                        if data1 is not None and data2 is not None:
                            rt1 = data1[data1['modality'] == modality]['reaction_time']
                            rt2 = data2[data2['modality'] == modality]['reaction_time']
                            if len(rt1) > 0 and len(rt2) > 0:
                                x1 = group_positions[modality-1] + (i - (n_datasets-1)/2) * bar_width
                                x2 = group_positions[modality-1] + (j - (n_datasets-1)/2) * bar_width
                                
                                bracket_height = global_max_height * (1.40 + 0.06 * (j-i))
                                
                                if self.ttest_radio.isChecked():
                                    t_stat, p_val = ttest_ind(rt1, rt2)
                                    stats_text += f"{item1.text()} v {item2.text()} p={p_val:.2e}, "
                                    if self.between_stats_checkbox.isChecked():
                                        self.draw_significance_brackets(ax, x1, x2,
                                                                     bracket_height,
                                                                     p_value=p_val,
                                                                     bracket_level=j-i,
                                                                     is_between_datasets=True)
                                else:
                                    t_stat, _ = ttest_ind(rt1, rt2)
                                    bf10 = bayesfactor_ttest(t=t_stat, nx=len(rt1), ny=len(rt2))
                                    if abs(bf10) > 1000:
                                        stats_text += f"{item1.text()} v {item2.text()} BF₁₀={bf10:.2e}, "
                                    else:
                                        stats_text += f"{item1.text()} v {item2.text()} BF₁₀={bf10:.2f}, "
                                    if self.between_stats_checkbox.isChecked():
                                        self.draw_significance_brackets(ax, x1, x2,
                                                                     bracket_height,
                                                                     bf10=bf10,
                                                                     bracket_level=j-i,
                                                                     is_between_datasets=True)
                stats_text = stats_text.rstrip(", ") + "\n"
    
        # Plot customization
        ax.set_xticks(group_positions)
        ax.set_xticklabels(['Audio', 'Visual', 'Audiovisual'])
        ax.set_xlabel('Modality')
        ax.set_ylabel('Reaction Time (ms)')
        ax.set_title('Median Reaction Times by Dataset')
        
        if self.show_legend_checkbox.isChecked():
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            self.figure.subplots_adjust(right=0.85)
    
        # Increase y-axis limit to accommodate all brackets
        self._set_y_limits(ax, 0, global_max_height * 1.5)

        figure_data = {
            'datasets': {}
        }
        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is not None:
                median_rt, std_error = self.calculate_median_rt(data)
                figure_data['datasets'][name] = {
                    'median_rt': median_rt.tolist(),
                    'std_error': std_error.tolist()
                }
        self.store_figure_data('median_rts', figure_data)
        self._customize_axes(ax)
        self.figure.tight_layout()
        self.canvas.draw()
        self.explanation_label.setText(stats_text)
        

    def plot_boxplot_rts(self):
        if not self.datasets:
            return
            
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
    
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.current_figure_type = 'boxplot_rts'
    
        all_data = []
        labels = []
        colors = []
        patterns = []  # Add list for patterns
        alphas = []    # Add list for alphas
        max_rt = 0
        min_rt = float('inf')
        
        modality_colors = {
            'Audio': 'red',
            'Visual': 'blue',
            'Audiovisual': 'purple'
        }
        
        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is None:
                continue
                
            # Get dataset pattern and alpha
            pattern = self.datasets[name]["pattern"]
            alpha = self.datasets[name].get("alpha", 0.7)  # Default alpha if not set
                
            for modality, mod_name in enumerate(['Audio', 'Visual', 'Audiovisual'], 1):
                mod_data = data[data['modality'] == modality]['reaction_time']
                all_data.append(mod_data)
                labels.append(f"{mod_name}\n{name}")
                colors.append(modality_colors[mod_name])
                patterns.append(pattern)  # Add pattern for this box
                alphas.append(alpha)      # Add alpha for this box
                
                # Track min and max values for y-axis limits
                if len(mod_data) > 0:
                    max_rt = max(max_rt, mod_data.max())
                    min_rt = min(min_rt, mod_data.min())
    
        if all_data:
            bp = ax.boxplot(all_data, labels=labels, patch_artist=True)
            
            # Color and style the boxes with patterns
            for i, (patch, color, pattern, alpha) in enumerate(zip(bp['boxes'], colors, patterns, alphas)):
                if pattern == 'clear':
                    patch.set_facecolor('none')
                elif pattern == 'solid':
                    patch.set_facecolor(color)
                else:
                    patch.set_facecolor('white')
                
                patch.set_edgecolor(color)
                patch.set_alpha(alpha)
                
                # Apply patterns
                if pattern == 'hatched':
                    patch.set_hatch('///')
                elif pattern == 'dotted':
                    patch.set_hatch('...')
                elif pattern == 'dashed':
                    patch.set_hatch('--')
                elif pattern == 'cross-hatched':
                    patch.set_hatch('xxx')
            
            # Style other boxplot elements
            plt.setp(bp['whiskers'], color='black')
            plt.setp(bp['caps'], color='black')
            plt.setp(bp['medians'], color='black')
            plt.setp(bp['fliers'], marker='o', markerfacecolor='gray', markersize=4)
    
            ax.set_title('Reaction Times by Dataset and Modality')
            ax.set_ylabel('Reaction Time (ms)')
            
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Add statistics between datasets
            if len(selected_items) > 1:
                stats_text = self.calculate_between_dataset_statistics(selected_items)
                self.explanation_label.setText(stats_text)
    
            # Set y-axis limits
            self._set_y_limits(ax, min_rt * 0.9, max_rt * 1.1)
    
            self._customize_axes(ax)
            self.figure.tight_layout()
    
            figure_data = {
                'datasets': {}
            }
            for item in selected_items:
                name = item.text()
                data = self.get_filtered_data(name)
                if data is not None:
                    figure_data['datasets'][name] = {
                        'Audio': data[data['modality'] == 1]['reaction_time'].tolist(),
                        'Visual': data[data['modality'] == 2]['reaction_time'].tolist(),
                        'Audiovisual': data[data['modality'] == 3]['reaction_time'].tolist()
                    }
            self.store_figure_data('boxplot_rts', figure_data)
    
            self.canvas.draw()

    def perform_anova_analysis(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select at least one dataset")
            return
    
        # Prepare combined dataset
        combined_data = []
        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is not None:
                data = data.copy()
                data['dataset'] = name
                combined_data.append(data)
        
        if not combined_data:
            return
            
        anova_data = pd.concat(combined_data, ignore_index=True)
        anova_data['modality'] = anova_data['modality'].map({1: 'Audio', 2: 'Visual', 3: 'Audiovisual'})
        
        # Perform ANOVA based on number of datasets
        if len(selected_items) == 1:
            # One-way ANOVA across modalities
            anova_results = anova(dv='reaction_time', 
                                between=['modality'],
                                data=anova_data, detailed=True)
            needed_cols = ['Source', 'SS', 'DF', 'F', 'p-unc', 'np2']
        else:
            # Two-way ANOVA with dataset factor
            anova_results = anova(dv='reaction_time', 
                                between=['modality', 'dataset'],
                                data=anova_data, detailed=True)
            needed_cols = ['Source', 'SS', 'DF', 'F', 'p-unc', 'np2']
        
        anova_results = anova_results[needed_cols]
        anova_results = anova_results.rename(columns={'p-unc': 'p'})
        
        if len(selected_items) > 1:
            # Replace interaction term with cleaner version
            anova_results['Source'] = anova_results['Source'].replace(
                'modality * dataset', 'modality × dataset'
            )
        
        # Clear and set up figure
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.axis('off')
        
        # Create table data with scientific notation
        table_data = []
        columns = list(anova_results.columns)
        for i in range(len(anova_results)):
            row = []
            for col in columns:
                val = anova_results.iloc[i][col]
                if pd.isna(val):
                    row.append('')
                elif isinstance(val, (int, float)):
                    if abs(val) >= 1000 or abs(val) < 0.001:
                        row.append(f'{val:.2e}')
                    else:
                        row.append(f'{val:.3f}')
                else:
                    row.append(str(val))
            table_data.append(row)
    
        # Create compact table
        table = ax.table(cellText=table_data,
                        colLabels=columns,
                        loc='center',
                        cellLoc='center',
                        bbox=[0.05, 0.3, 0.9, 0.5])
        
        # Formatting
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        
        # Adjust cell properties
        for (row, col), cell in table.get_celld().items():
            if row == 0:  # Header row
                cell.set_facecolor('#E6E6E6')
                cell.set_text_props(weight='bold')
            if col == 0 and row > 0:  # Source column, non-header
                if 'modality × dataset' in cell.get_text().get_text():
                    cell._text.set_text('modality\n×\ndataset')
                    cell.set_text_props(linespacing=1.2)
        
        # Scale table
        table.scale(0.8, 0.7)
        self.canvas.draw()
        
        # Generate explanation text
        if len(selected_items) == 1:
            explanation = f"One-way ANOVA Results for {selected_items[0].text()}:\n\n"
            
            # Modality effect only
            row = anova_results.loc[anova_results['Source'] == 'modality']
            if not row.empty:
                p_val = row['p'].values[0]
                np2_val = row['np2'].values[0]
                f_val = row['F'].values[0]
                
                explanation += f"Modality effect: F = {f_val:.2f}, p = {p_val:.4f}, np2 = {np2_val:.3f}\n"
                
                # Effect size interpretation
                if np2_val < 0.01:
                    effect_size = "minimal"
                elif np2_val < 0.06:
                    effect_size = "small"
                elif np2_val < 0.14:
                    effect_size = "medium"
                else:
                    effect_size = "large"
                explanation += f"({effect_size} effect size)\n\n"
        else:
            explanation = "Two-way ANOVA Results:\n\n"
            
            # Main effects
            for effect in ['modality', 'dataset']:
                row = anova_results.loc[anova_results['Source'] == effect]
                if not row.empty:
                    p_val = row['p'].values[0]
                    np2_val = row['np2'].values[0]
                    f_val = row['F'].values[0]
                    
                    explanation += f"{effect.capitalize()} main effect: F = {f_val:.2f}, p = {p_val:.4f}, np2 = {np2_val:.3f}\n"
                    
                    if np2_val < 0.01:
                        effect_size = "minimal"
                    elif np2_val < 0.06:
                        effect_size = "small"
                    elif np2_val < 0.14:
                        effect_size = "medium"
                    else:
                        effect_size = "large"
                    explanation += f"({effect_size} effect size)\n\n"
            
            # Interaction effect
            interaction_row = anova_results.loc[anova_results['Source'] == 'modality × dataset']
            if not interaction_row.empty:
                p_val = interaction_row['p'].values[0]
                np2_val = interaction_row['np2'].values[0]
                f_val = interaction_row['F'].values[0]
                
                explanation += f"Interaction effect: F = {f_val:.2f}, p = {p_val:.4f}, np2 = {np2_val:.3f}\n"
                
                if np2_val < 0.01:
                    effect_size = "minimal"
                elif np2_val < 0.06:
                    effect_size = "small"
                elif np2_val < 0.14:
                    effect_size = "medium"
                else:
                    effect_size = "large"
                explanation += f"({effect_size} interaction effect)\n\n"
        
        explanation += "Effect size interpretation:\n"
        explanation += "np2: 0.01=small, 0.06=medium, 0.14=large"
        
        self.explanation_label.setText(explanation)

    def _calculate_y_limits(self, values, errors=None, padding_top=0.25, padding_bottom=0.1):
        """
        Calculate appropriate y-axis limits based on data values.
        
        Args:
            values: Array of y-axis values
            errors: Optional array of error values
            padding_top: Percentage of range to add as padding on top (0.25 = 25%)
            padding_bottom: Percentage of range to add as padding on bottom (0.1 = 10%)
        """
        if errors is not None:
            max_val = np.nanmax(values + errors)
            min_val = np.nanmin(values - errors)
        else:
            max_val = np.nanmax(values)
            min_val = np.nanmin(values)
            
        # Calculate range and add padding
        range_val = max_val - min_val
        ymax = max_val + (padding_top * range_val)
        ymin = max(0, min_val - (padding_bottom * range_val))  # Don't go below 0 for RT data
        
        return ymin, ymax

    def _set_y_limits(self, ax, ymin, ymax):
        """
        Set y-axis limits, taking into account manual user input if provided.
        """
        # Override with user input if provided
        if self.ymin_input.text():
            try:
                user_ymin = float(self.ymin_input.text())
                ymin = user_ymin
            except ValueError:
                pass
                
        if self.ymax_input.text():
            try:
                user_ymax = float(self.ymax_input.text())
                ymax = user_ymax
            except ValueError:
                pass
        
        # Update the input fields with current values
        self.ymin_input.setText(f"{ymin:.0f}")
        self.ymax_input.setText(f"{ymax:.0f}")
        
        # Set the axis limits
        ax.set_ylim(ymin, ymax)

    def perform_statistical_test(self, data, measure='mean'):
        modalities = ['Audio', 'Visual', 'Audiovisual']
        p_values = []
        test_results = []

        for i in range(len(modalities)):
            for j in range(i + 1, len(modalities)):
                mod1 = data[data['modality'] == i + 1]['reaction_time']
                mod2 = data[data['modality'] == j + 1]['reaction_time']

                if self.ttest_radio.isChecked():
                    t_stat, p_value = ttest_ind(mod1, mod2)
                    # Calculate effect size (Cohen's d)
                    pooled_std = np.sqrt(((len(mod1) - 1) * mod1.std() ** 2 + 
                                        (len(mod2) - 1) * mod2.std() ** 2) / 
                                        (len(mod1) + len(mod2) - 2))
                    cohen_d = (mod1.mean() - mod2.mean()) / pooled_std
                    test_results.append((t_stat, p_value, cohen_d))
                    p_values.append(p_value)
                else:  # Bayes Factor
                    t_stat, p_value = ttest_ind(mod1, mod2)
                    bf10 = bayesfactor_ttest(t=float(t_stat), nx=len(mod1), ny=len(mod2))
                    bf10 = float(bf10)  # Convert bf10 to a float
                    bf01 = 1 / bf10 if bf10 > 0 else float('inf')
                    
                    # Format BF10 to scientific notation if > 1000
                    if (bf10 > 1000):
                        bf10 = f"{bf10:.2e}"
                    else:
                        bf10 = f"{bf10:.2f}"
                    
                    test_results.append((bf10, bf01, None))
                    p_values.append(bf01)

        return p_values, test_results

    def get_significance_symbol(self, p_value):
        if (p_value < 0.001):
            return '***'
        elif (p_value < 0.01):
            return '**'
        elif (p_value < 0.05):
            return '*'
        else:
            return ''

    def plot_participant_distribution(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
            
        self.figure.clear()
        
        # Calculate grid dimensions
        n_datasets = len(selected_items)
        n_cols = int(np.ceil(np.sqrt(n_datasets)))
        n_rows = int(np.ceil(n_datasets / n_cols))
    
        # Create subplots within the existing figure
        axs = self.figure.subplots(nrows=n_rows, ncols=n_cols)
        axs = np.atleast_1d(axs).flatten()
        
        # Get y-axis limits
        try:
            ymin = float(self.ymin_input.text())
            ymax = float(self.ymax_input.text())
        except ValueError:
            ymin = None
            ymax = None
    
        for idx, item in enumerate(selected_items):
            dataset_name = item.text()
            data = self.get_filtered_data(dataset_name)
            if data is None:
                continue
    
            ax = axs[idx]
    
            excluded_participants = self.excluded_participants.get(dataset_name, [])
    
            for participant in data['participant_number'].unique():
                if participant in excluded_participants:
                    continue
    
                participant_data = data[data['participant_number'] == participant]
                median_rt = participant_data.groupby('modality')['reaction_time'].median()
    
                if len(median_rt) == 3:
                    ax.plot(['Audio', 'Visual', 'Audiovisual'], median_rt, '-o',
                           label=f'P{participant}', markersize=2)
    
            # Customize subplot
            ax.set_title(f'{dataset_name}')
            ax.set_xlabel('Modality')
            ax.set_ylabel('Reaction Time (ms)')
            # Remove top and right axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            if ymin is not None and ymax is not None:
                ax.set_ylim(ymin, ymax)
            if self.show_legend_checkbox.isChecked():
                ax.legend(loc='best', fontsize=6)
    
        # Hide any unused subplots
        for idx in range(len(selected_items), len(axs)):
            axs[idx].set_visible(False)

        figure_data = {
            'datasets': {}
        }
        for idx, item in enumerate(selected_items):
            dataset_name = item.text()
            data = self.get_filtered_data(dataset_name)
            if data is not None:
                figure_data['datasets'][dataset_name] = {
                    'participants': {}
                }
                for participant in data['participant_number'].unique():
                    participant_data = data[data['participant_number'] == participant]
                    median_rt = participant_data.groupby('modality')['reaction_time'].median()
                    if len(median_rt) == 3:
                        figure_data['datasets'][dataset_name]['participants'][str(participant)] = {
                            'Audio': median_rt[1],
                            'Visual': median_rt[2],
                            'Audiovisual': median_rt[3]
                        }
        self.store_figure_data('participant_distribution', figure_data)

        self.figure.tight_layout()
        self.canvas.draw()

    def get_excluded_participants(self):
        if self.participant_selector.currentText() == "All Participants":
            return self.excluded_participants
        else:
            return []

    def is_outlier(self, median_rt):
        z_scores = np.abs(stats.zscore(median_rt))
        return np.any(z_scores > 2)

    def plot_race_model(self):
        if not self.datasets:
            return
            
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
    
        self.figure.clear()
        self.figure.set_size_inches(8, 5)  # Base canvas size
        
        # Calculate grid dimensions
        n_datasets = len(selected_items)
        n_cols = int(np.ceil(np.sqrt(n_datasets)))
        n_rows = int(np.ceil(n_datasets / n_cols))
        
        # Adjust figure size based on grid
        if n_rows > 1:
            self.figure.set_size_inches(8, 5 * (n_rows/2))  # Scale height with rows
    
        # Create subplots with optimized spacing
        self.figure.subplots_adjust(
            left=0.1,
            right=0.95,
            bottom=0.1,
            top=0.9,
            wspace=0.4,  # Increased horizontal spacing
            hspace=0.5   # Increased vertical spacing
        )
        axs = self.figure.subplots(nrows=n_rows, ncols=n_cols)
        axs = np.atleast_1d(axs).flatten()
        
        all_stats = []
        
        for idx, item in enumerate(selected_items):
            name = item.text()
            ax = axs[idx]
            
            data = self.datasets[name]["data"]
            color = self.datasets[name]["color"]
            
            percentile_range = (self.percentile_range_slider.first_position,
                              self.percentile_range_slider.second_position)
            
            violation, common_rts, ecdf_a, ecdf_v, ecdf_av, race_model = \
                self.calculate_race_violation(data, percentile_range)
    
            # Plot CDFs
            ax.plot(common_rts, ecdf_a, label='Audio', color='red', linewidth=1.5)
            ax.plot(common_rts, ecdf_v, label='Visual', color='blue', linewidth=1.5)
            ax.plot(common_rts, ecdf_av, label='AV', color='purple', linewidth=1.5)  # Shortened label
            ax.plot(common_rts, race_model, label='Race', color='black', 
                    linestyle='--', linewidth=1)  # Shortened label
    
            # Shade violations
            violations = ecdf_av > race_model
            lower_idx = np.searchsorted(ecdf_av, percentile_range[0] / 100)
            upper_idx = np.searchsorted(ecdf_av, percentile_range[1] / 100)
            ax.fill_between(common_rts[lower_idx:upper_idx],
                           race_model[lower_idx:upper_idx],
                           ecdf_av[lower_idx:upper_idx],
                           where=violations[lower_idx:upper_idx],
                           color='red', alpha=0.2)  # Reduced alpha
    
            # Smaller title with single line
            ax.set_title(name, pad=5, fontsize=9)
            
            if idx >= (n_rows-1) * n_cols:  # Bottom row
                ax.set_xlabel('RT (ms)', fontsize=8)
            if idx % n_cols == 0:  # Leftmost column
                ax.set_ylabel('Probability', fontsize=8)
            
            # Optimize legend
            ax.legend(fontsize=7, loc='lower right', 
                     bbox_to_anchor=(0.98, 0.02),
                     borderaxespad=0,
                     frameon=False,
                     ncol=2)  # Two columns for legend
            
            # Remove unnecessary spines and ticks
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(axis='both', which='major', labelsize=8)
            
            # Calculate statistics
            violation_area = np.sum(np.maximum(ecdf_av - race_model, 0))
            violation_max = np.max(ecdf_av - race_model)
            violation_percent = (np.sum(violations) / len(violations)) * 100
            
            all_stats.append({
                'name': name,
                'area': violation_area,
                'max': violation_max,
                'percent': violation_percent
            })
    
        # Hide unused subplots
        for idx in range(len(selected_items), len(axs)):
            axs[idx].set_visible(False)
    
        # Format statistics text
        stats_text = "Race Model Violation Statistics:\n\n"
        column_format = "{:<12}| Area:{:.3f} | Max:{:.3f} | Viol:{:.1f}%"
        chars_per_col = 40
        canvas_width = 80
        items_per_row = max(1, canvas_width // chars_per_col)
        
        for i in range(0, len(all_stats), items_per_row):
            row_stats = all_stats[i:i + items_per_row]
            row_text = []
            for stat in row_stats:
                row_text.append(column_format.format(
                    stat['name'][:12],
                    stat['area'],
                    stat['max'],
                    stat['percent']
                ))
            stats_text += "  ".join(row_text) + "\n"
        
        figure_data = {
            'datasets': {}
        }
        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is not None:
                violation, common_rts, ecdf_a, ecdf_v, ecdf_av, race_model = \
                    self.calculate_race_violation(data, percentile_range)
                figure_data['datasets'][name] = {
                    'common_rts': common_rts.tolist(),
                    'ecdf_audio': ecdf_a.tolist(),
                    'ecdf_visual': ecdf_v.tolist(),
                    'ecdf_av': ecdf_av.tolist(),
                    'race_model': race_model.tolist()
                }
        self.store_figure_data('race_model', figure_data)
        self.explanation_label.setText(stats_text)
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_race_violations(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return

        self.figure.clear()
        self.figure.set_size_inches(8, 5)
        ax = self.figure.add_subplot(111)
        self.current_figure_type = 'race_violations'

        percentile_range = (self.percentile_range_slider.first_position,
                        self.percentile_range_slider.second_position)

        violation_stats = {}
        figure_data = {'datasets': {}}

        for item in selected_items:
            name = item.text()
            data = self.get_filtered_data(name)
            if data is None:
                continue

            color = self.datasets[name]["color"]

            result = self.calculate_race_violation(data, percentile_range)
            # Check if result is None
            if result is None:
                # Skip this dataset if we cannot compute race violation
                continue

            violation, common_rts, ecdf_a, ecdf_v, ecdf_av, race_model = result

            violations = ecdf_av - race_model

            if self.use_percentiles_checkbox.isChecked():
                # If using percentiles, ensure we have valid data. If not, skip.
                if len(common_rts) == 0:
                    continue

            if self.use_percentiles_checkbox.isChecked():
                av_data = data[data['modality'] == 3]['reaction_time'].values
                x_axis = np.array([scipy.stats.percentileofscore(av_data, rt) for rt in common_rts])
                xlabel = 'Percentile'
            else:
                x_axis = common_rts
                xlabel = 'Reaction Time (ms)'

            ax.plot(x_axis, violations, color=color, label=name, linewidth=2)
            ax.fill_between(x_axis, violations, 0, where=(violations > 0),
                        color=color, alpha=0.3)

            violation_stats[name] = {
                'max': np.max(violations),
                'mean': np.mean(violations),
                'total': np.sum(violations[violations > 0]),
                'percent': (np.sum(violations > 0) / len(violations)) * 100,
                'reaction_times': x_axis,
                'violations': violations
            }

            figure_data['datasets'][name] = {
                'reaction_times': x_axis.tolist(),
                'violations': violations.tolist(),
                'statistics': {
                    'max': float(np.max(violations)),
                    'mean': float(np.mean(violations)),
                    'total': float(np.sum(violations[violations > 0])),
                    'percent': float((np.sum(violations > 0) / len(violations)) * 100)
                }
            }

        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Violation Magnitude')
        ax.set_title('Race Model Violations by Dataset')

        if self.show_legend_checkbox.isChecked():
            ax.legend(loc='best', frameon=False)

        stats_text = "Race Model Violation Statistics:\n\n"
        column_format = "{:<15} | Maximum: {:.3f} | Mean: {:.3f} | Total: {:.3f} | Violations: {:.1f}%"
        chars_per_col = 80
        canvas_width = 120
        items_per_row = max(1, canvas_width // chars_per_col)
        
        dataset_names = list(violation_stats.keys())
        n_rows = int(np.ceil(len(dataset_names) / items_per_row))

        for row in range(n_rows):
            row_text = []
            for col in range(items_per_row):
                idx = row * items_per_row + col
                if idx < len(dataset_names):
                    name = dataset_names[idx]
                    stats = violation_stats[name]
                    row_text.append(column_format.format(
                        name[:15],
                        stats['max'],
                        stats['mean'],
                        stats['total'],
                        stats['percent']
                    ))
            stats_text += "\n".join(row_text) + "\n"

        self.store_figure_data('race_violations', figure_data)
        self.explanation_label.setText(stats_text)
        self._customize_axes(ax)
        self.figure.tight_layout()
        self.canvas.draw()



    def plot_single_dataset_violations(self, dataset_name, ax):
        """Plot race violations for a single dataset"""
        data = self.get_filtered_data(dataset_name)
        if data is None:
            return None

        percentile_range = (self.percentile_range_slider.first_position,
                           self.percentile_range_slider.second_position)
        _, common_rts, _, _, ecdf_av, race_model = self.calculate_race_violation(data, percentile_range)

        # Calculate violations
        violations = ecdf_av - race_model

        if self.use_percentiles_checkbox.isChecked():
            av_data = data[data['modality'] == 3]['reaction_time']
            x_axis = np.array([stats.percentileofscore(av_data, rt) for rt in common_rts])
            xlabel = 'Percentile'
        else:
            x_axis = common_rts
            xlabel = 'Reaction Time (ms)'

        # Plot violations
        ax.plot(x_axis, violations, color='black', linewidth=2)
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax.fill_between(x_axis, violations, 0, where=(violations > 0),
                       color='red', alpha=0.3)

        # Calculate statistics
        positive_violations = violations[violations > 0]
        stats = {
            'max': np.max(violations),
            'mean': np.mean(violations),
            'total': np.sum(positive_violations),
            'percent': (len(positive_violations)/len(violations))*100
        }

        # Add statistics to plot
        stats_text = (f"Max: {stats['max']:.3f}\n"
                     f"Mean: {stats['mean']:.3f}\n"
                     f"Total: {stats['total']:.3f}")
        ax.text(0.02, 0.98, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                fontsize=8)

        ax.set_title(f'{dataset_name}\nRace Model Violations')
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Violation Magnitude')
        self._customize_axes(ax)
        
        return violations

    def compare_dataset_violations(self, violations_dict):
        """Compare violations between datasets statistically"""
        stats_text = ""
        datasets = list(violations_dict.keys())
        
        for i in range(len(datasets)):
            for j in range(i + 1, len(datasets)):
                name1, name2 = datasets[i], datasets[j]
                v1, v2 = violations_dict[name1], violations_dict[name2]
                
                if self.ttest_radio.isChecked():
                    t_stat, p_val = ttest_ind(v1, v2)
                    stats_text += (f"{name1} vs {name2}:\n"
                                 f"t = {t_stat:.2f}, p = {p_val:.4f}\n")
                    if p_val < 0.05:
                        mean_diff = np.mean(v1) - np.mean(v2)
                        stats_text += f"Mean difference: {mean_diff:.3f}\n"
                else:
                    t_stat, _ = ttest_ind(v1, v2)
                    bf10 = bayesfactor_ttest(t=t_stat, nx=len(v1), ny=len(v2))
                    stats_text += (f"{name1} vs {name2}:\n"
                                 f"BF₁₀ = {bf10:.2f}\n"
                                 f"{self.interpret_bayes_factor(bf10)}\n")
                stats_text += "\n"
                
        return stats_text

    def calculate_race_violation(self, participant_data, percentile_range):
        rt_a = participant_data[participant_data['modality'] == 1]['reaction_time']
        rt_v = participant_data[participant_data['modality'] == 2]['reaction_time']
        rt_av = participant_data[participant_data['modality'] == 3]['reaction_time']

        # Check if any modality is empty
        if rt_a.empty or rt_v.empty or rt_av.empty:
            return None  # Cannot calculate without all three modalities

        # Check for NaNs or identical min/max
        if pd.isna(rt_a.min()) or pd.isna(rt_v.min()) or pd.isna(rt_av.min()):
            return None
        min_val = min(rt_a.min(), rt_v.min(), rt_av.min())
        max_val = max(rt_a.max(), rt_v.max(), rt_av.max())
        if min_val == max_val:
            return None  # no variability

        common_rts = np.linspace(min_val, max_val, 500)

        # Double-check lengths before interpolation
        if len(rt_a) == 0 or len(rt_v) == 0 or len(rt_av) == 0:
            return None

        ecdf_a = np.interp(common_rts, np.sort(rt_a), np.arange(1, len(rt_a) + 1) / len(rt_a))
        ecdf_v = np.interp(common_rts, np.sort(rt_v), np.arange(1, len(rt_v) + 1) / len(rt_v))
        ecdf_av = np.interp(common_rts, np.sort(rt_av), np.arange(1, len(rt_av) + 1) / len(rt_av))

        selected_model = self.model_selector.currentText()
        if selected_model == "Standard Race Model":
            race_model = 1 - (1 - ecdf_a) * (1 - ecdf_v)
        elif selected_model == "Coactivation Model":
            mean_c = self.coactivation_mean_slider.value()
            std_c = self.coactivation_std_slider.value()
            race_model = stats.norm.cdf(common_rts, loc=mean_c, scale=std_c)
        elif selected_model == "Parallel Interactive Race Model":
            gamma = self.pir_interaction_slider.value() / 100
            race_model = 1 - (1 - ecdf_a) * (1 - ecdf_v) * (1 - gamma * np.minimum(ecdf_a, ecdf_v))
        elif selected_model == "Multisensory Response Enhancement Model":
            alpha = self.mre_alpha_slider.value() / 100
            beta = self.mre_beta_slider.value() / 100
            lambda_param = self.mre_lambda_slider.value() / 100
            race_model = alpha * ecdf_a + beta * ecdf_v + lambda_param * (ecdf_a * ecdf_v)
        else:
            return None

        race_model = np.clip(race_model, 0, 1)
        violations = np.maximum(ecdf_av - race_model, 0)

        lower_percentile, upper_percentile = percentile_range
        lower_idx = int(len(violations) * lower_percentile / 100)
        upper_idx = int(len(violations) * upper_percentile / 100)

        return np.mean(violations[lower_idx:upper_idx]), common_rts, ecdf_a, ecdf_v, ecdf_av, race_model


    def update_slider_visibility(self):
        show_sliders = 'Race Violations' in [self.factor1_selector.currentText(), self.factor2_selector.currentText()]
        self.percentile_range_slider.setVisible(show_sliders)
        self.percentile_range_slider_label.setVisible(show_sliders)

    def update_percentile_range_label(self, start, end):
        self.percentile_range_slider_label.setText(
            f'Include Trials Within CDF Range: {start}% - {end}%\n(trials outside range will be excluded)'
        )

    def calculate_interquartile_range(self, participant_data, modality=None):
        if modality:
            data = participant_data[participant_data['modality'] == modality]['reaction_time']
        else:
            data = participant_data['reaction_time']
        q75, q25 = np.percentile(data, [75, 25])
        return q75 - q25

    def calculate_race_violation(self, participant_data, percentile_range):
        rt_a = participant_data[participant_data['modality'] == 1]['reaction_time']
        rt_v = participant_data[participant_data['modality'] == 2]['reaction_time']
        rt_av = participant_data[participant_data['modality'] == 3]['reaction_time']

        common_rts = np.linspace(min(rt_a.min(), rt_v.min(), rt_av.min()),
                                 max(rt_a.max(), rt_v.max(), rt_av.max()), 500)

        ecdf_a = np.interp(common_rts, np.sort(rt_a), np.arange(1, len(rt_a) + 1) / len(rt_a))
        ecdf_v = np.interp(common_rts, np.sort(rt_v), np.arange(1, len(rt_v) + 1) / len(rt_v))
        ecdf_av = np.interp(common_rts, np.sort(rt_av), np.arange(1, len(rt_av) + 1) / len(rt_av))

        selected_model = self.model_selector.currentText()
        if selected_model == "Standard Race Model":
            race_model = 1 - (1 - ecdf_a) * (1 - ecdf_v)
        elif selected_model == "Coactivation Model":
            mean_c = self.coactivation_mean_slider.value()
            std_c = self.coactivation_std_slider.value()
            race_model = stats.norm.cdf(common_rts, loc=mean_c, scale=std_c)
        elif selected_model == "Parallel Interactive Race Model":
            gamma = self.pir_interaction_slider.value() / 100
            race_model = 1 - (1 - ecdf_a) * (1 - ecdf_v) * (1 - gamma * np.minimum(ecdf_a, ecdf_v))
        elif selected_model == "Multisensory Response Enhancement Model":
            alpha = self.mre_alpha_slider.value() / 100
            beta = self.mre_beta_slider.value() / 100
            lambda_param = self.mre_lambda_slider.value() / 100
            race_model = alpha * ecdf_a + beta * ecdf_v + lambda_param * (ecdf_a * ecdf_v)

        race_model = np.clip(race_model, 0, 1)
        violations = np.maximum(ecdf_av - race_model, 0)

        lower_percentile, upper_percentile = percentile_range
        lower_idx = int(len(violations) * lower_percentile / 100)
        upper_idx = int(len(violations) * upper_percentile / 100)
        return np.mean(violations[lower_idx:upper_idx]), common_rts, ecdf_a, ecdf_v, ecdf_av, race_model

    def plot_scatter(self):
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            return
        
        self.figure.clear()
        self.anova_table.setVisible(False)
        self.current_figure_type = 'scatter'
    
        n_datasets = len(selected_items)
        n_cols = int(np.ceil(np.sqrt(n_datasets)))
        n_rows = int(np.ceil(n_datasets / n_cols))
    
        axs = self.figure.subplots(nrows=n_rows, ncols=n_cols)
        axs = np.atleast_1d(axs).flatten()
        
        stats_text = "Correlation Statistics:\n\n"
        
        # Track global min/max for axis syncing
        global_xlim = [float('inf'), float('-inf')]
        global_ylim = [float('inf'), float('-inf')]
    
        for idx, item in enumerate(selected_items):
            dataset_name = item.text()
            data = self.get_filtered_data(dataset_name)
            if data is None:
                continue
    
            ax = axs[idx]
            factor1 = self.factor1_selector.currentText()
            factor2 = self.factor2_selector.currentText()
            percentile_range = (self.percentile_range_slider.first_position, 
                                self.percentile_range_slider.second_position)
    
            participants = data['participant_number'].unique()
            excluded_participants = self.excluded_participants.get(dataset_name, [])
    
            x_values = []
            y_values = []
            colors = plt.cm.tab20(np.linspace(0, 1, len(participants)))
            color_map = {participant: colors[i] for i, participant in enumerate(participants)}
    
            for participant in participants:
                if participant in excluded_participants:
                    continue
                participant_data = data[data['participant_number'] == participant]
    
                x_value = self.get_factor_value(participant_data, factor1, percentile_range)
                y_value = self.get_factor_value(participant_data, factor2, percentile_range)
    
                if x_value is not None and y_value is not None:
                    x_values.append(x_value)
                    y_values.append(y_value)
                    ax.scatter(x_value, y_value, color=color_map[participant], 
                               label=f'P{participant}', s=25)
            
            if x_values and y_values:
                # Update global limits
                global_xlim[0] = min(global_xlim[0], min(x_values))
                global_xlim[1] = max(global_xlim[1], max(x_values))
                global_ylim[0] = min(global_ylim[0], min(y_values))
                global_ylim[1] = max(global_ylim[1], max(y_values))
    
            # Add line of best fit if enough points
            if len(x_values) > 1 and len(y_values) > 1:
                x = np.array(x_values)
                y = np.array(y_values)
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                
                x_line = np.linspace(min(x), max(x), 100)
                ax.plot(x_line, intercept + slope * x_line, 'r', linewidth=1)
                
                equation = f'y = {slope:.2f}x + {intercept:.2f}\nR² = {r_value**2:.2f}'
                ax.text(0.05, 0.95, equation, transform=ax.transAxes, fontsize=8,
                        verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))
                
                stats_text += f"{dataset_name}:\n"
                stats_text += f"r = {r_value:.2f}, p = {p_value:.2f}\n"
                if p_value < 0.05:
                    stats_text += "Significant correlation at p < 0.05\n"
                stats_text += "\n"
    
            ax.set_title(f'{dataset_name}')
            ax.set_xlabel(factor1)
            ax.set_ylabel(factor2)

            # Remove top and right axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            if self.show_legend_checkbox.isChecked():
                ax.legend(loc='best', fontsize=6)

        # Apply synced axes if checkbox is checked
            if self.sync_axes_checkbox.isChecked():
                # Calculate 5% buffer
                x_range = global_xlim[1] - global_xlim[0]
                y_range = global_ylim[1] - global_ylim[0]
                x_buffer = x_range * 0.05
                y_buffer = y_range * 0.05
                
                # Apply buffered limits to all subplots
                for ax in axs[:len(selected_items)]:
                    ax.set_xlim(global_xlim[0] - x_buffer, global_xlim[1] + x_buffer)
                    ax.set_ylim(global_ylim[0] - y_buffer, global_ylim[1] + y_buffer)
        
        # Hide unused subplots
        for idx in range(len(selected_items), len(axs)):
            axs[idx].set_visible(False)
    
            figure_data = {
                'datasets': {}
            }
            for idx, item in enumerate(selected_items):
                dataset_name = item.text()
                data = self.get_filtered_data(dataset_name)
                if data is not None:
                    figure_data['datasets'][dataset_name] = {
                        'x_values': x_values,
                        'y_values': y_values,
                        'factor1': factor1,
                        'factor2': factor2,
                        'correlation': {
                            'r_value': r_value,
                            'p_value': p_value,
                            'slope': slope,
                            'intercept': intercept
                        }
                    }
            self.store_figure_data('scatter', figure_data)   

        self.figure.tight_layout()
        self.canvas.draw()
        self.explanation_label.setText(stats_text)
    
    def handle_custom_factor_selection(self, text):
        if text == "Custom Column...":
            # Get currently selected dataset (assuming one dataset selected)
            selected_items = self.dataset_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
                return

            dataset_name = selected_items[0].text()
            data = self.datasets[dataset_name]["data"]
            all_columns = data.columns.tolist()

            # Let user pick a column
            column, ok = QInputDialog.getItem(self, "Select Column", "Choose a column from the dataset:", all_columns, 0, False)
            if ok:
                # Update the selector text to show this chosen column
                sender = self.sender()  # The combo box that triggered this
                sender.blockSignals(True)  # Temporarily block signals to avoid recursion
                sender.setCurrentText(column)  # Set chosen column as the current text
                sender.blockSignals(False)


    def get_factor_value(self, participant_data, factor, percentile_range):
        if factor == 'Age':
            return pd.to_numeric(participant_data['SubjectAge'].iloc[0], errors='coerce')
        elif factor == 'Interquartile Range (Total)':
            return self.calculate_interquartile_range(participant_data)
        elif factor == 'Interquartile Range (Audio)':
            return self.calculate_interquartile_range(participant_data, modality=1)
        elif factor == 'Interquartile Range (Visual)':
            return self.calculate_interquartile_range(participant_data, modality=2)
        elif factor == 'Interquartile Range (Audiovisual)':
            return self.calculate_interquartile_range(participant_data, modality=3)
        elif factor == 'Race Violations':
            # Check if all three modalities (A, V, AV) are present
            has_a = (participant_data['modality'] == 1).any()
            has_v = (participant_data['modality'] == 2).any()
            has_av = (participant_data['modality'] == 3).any()
            
            if not (has_a and has_v and has_av):
                # Missing one of the modalities, cannot calculate race violations
                return None
            
            result = self.calculate_race_violation(participant_data, percentile_range)
            if result is None or any(r is None for r in result):
                return None
            
            _, common_rts, ecdf_a, ecdf_v, ecdf_av, race_model = result
            if (common_rts is None) or (ecdf_av is None) or (race_model is None):
                return None
            
            lower_idx = np.searchsorted(ecdf_av, percentile_range[0] / 100)
            upper_idx = np.searchsorted(ecdf_av, percentile_range[1] / 100)
            cumulative_violation = np.sum(np.maximum(ecdf_av[lower_idx:upper_idx] - race_model[lower_idx:upper_idx], 0))
            return cumulative_violation
        elif factor == 'Total Trials':
            return len(participant_data)
        elif factor == 'Mean RT (Audio)':
            return participant_data[participant_data['modality'] == 1]['reaction_time'].mean()
        elif factor == 'Mean RT (Visual)':
            return participant_data[participant_data['modality'] == 2]['reaction_time'].mean()
        elif factor == 'Mean RT (Audiovisual)':
            return participant_data[participant_data['modality'] == 3]['reaction_time'].mean()
        elif factor == 'Median RT (Audio)':
            return participant_data[participant_data['modality'] == 1]['reaction_time'].median()
        elif factor == 'Median RT (Visual)':
            return participant_data[participant_data['modality'] == 2]['reaction_time'].median()
        elif factor == 'Median RT (Audiovisual)':
            return participant_data[participant_data['modality'] == 3]['reaction_time'].median()
        else:
            # For custom columns
            if factor in participant_data.columns:
                vals = participant_data[factor]
                vals_numeric = pd.to_numeric(vals, errors='coerce')
                if not vals_numeric.isna().all():
                    return vals_numeric.mean()
                else:
                    return vals.dropna().iloc[0] if not vals.dropna().empty else None
            else:
                return None



    def save_figure(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Figure", "", "PNG Files (*.png);;EPS Files (*.eps);;SVG Files (*.svg);;All Files (*)", options=options)
        if file_path:
            if not (file_path.lower().endswith('.png') or file_path.lower().endswith('.eps') or file_path.lower().endswith('.svg')):
                file_path += '.png'  # Default to PNG if no extension is provided
            self.figure.savefig(file_path)
            self.statusBar().showMessage('Figure saved successfully!', 5000)

    def save_figure_data(self):
        if not self.current_figure_type or self.current_figure_type not in self.figure_data:
            QMessageBox.warning(self, "No Data", "No figure data available to save.")
            return
    
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure Data", "",
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)", 
            options=options
        )
    
        if not file_path:
            return
            
        try:
            data = self.figure_data[self.current_figure_type]
            
            if file_path.lower().endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)
            else:
                # Convert nested dict to DataFrame
                rows = []
                for dataset, values in data['datasets'].items():
                    for key, value in values.items():
                        if isinstance(value, (list, np.ndarray)):
                            for i, v in enumerate(value):
                                rows.append({
                                    'Dataset': dataset,
                                    'Measure': key,
                                    'Index': i,
                                    'Value': v
                                })
                
                df = pd.DataFrame(rows)
                df.to_csv(file_path, index=False)
                
            self.statusBar().showMessage(f'Figure data saved to {file_path}', 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save figure data: {str(e)}")

    def show_more_info(self):
        info_text = """
        <h2>Race Model Types</h2>

        <h3>1. Standard Race Model (Probability Summation Model)</h3>
        <p>This model assumes independent and parallel processing of stimuli from different sensory modalities. The reaction time for audiovisual (AV) stimuli is predicted by the probability that either the auditory (A) or visual (V) signal will trigger a response first.</p>
        <p>Formula: P(RT ≤ t)_AV = P(RT ≤ t)_A + P(RT ≤ t)_V - [P(RT ≤ t)_A * P(RT ≤ t)_V]</p>
        <p>This model serves as a baseline and does not have adjustable parameters.</p>

        <h3>2. Coactivation Model</h3>
        <p>This model assumes that information from different sensory channels is combined and integrated at some level of processing. It predicts stronger facilitation effects than the standard race model.</p>
        <p>Formula: P(RT ≤ t)_AV = Φ((t - μ_c) / σ_c)</p>
        <p>Parameters:</p>
        <ul>
            <li><strong>Mean (μ_c):</strong> The average reaction time for the combined AV stimulus. A lower value indicates faster overall processing.</li>
            <li><strong>Standard Deviation (σ_c):</strong> The variability in reaction times. A lower value suggests more consistent responses.</li>
        </ul>

        <h3>3. Parallel Interactive Race Model</h3>
        <p>This model extends the standard race model by allowing interactions between the sensory channels. The processing of auditory information might speed up the processing of visual information, or vice versa.</p>
        <p>Formula: P(RT ≤ t)_AV = P(RT ≤ t)_A + P(RT ≤ t)_V - [P(RT ≤ t)_A * P(RT ≤ t)_V] + γ * min(P(RT ≤ t)_A, P(RT ≤ t)_V)</p>
        <p>Parameter:</p>
        <ul>
            <li><strong>Interaction (γ):</strong> Represents the strength of interaction between modalities. A higher value indicates stronger cross-modal facilitation.</li>
        </ul>

        <h3>4. Multisensory Response Enhancement Model</h3>
        <p>This model posits that multisensory stimuli can lead to a nonlinear enhancement of response probabilities, beyond what would be predicted by simple summation.</p>
        <p>Formula: P(RT ≤ t)_AV = α * P(RT ≤ t)_A + β * P(RT ≤ t)_V + λ * [P(RT ≤ t)_A * P(RT ≤ t)_V]</p>
        <p>Parameters:</p>
        <ul>
            <li><strong>α (Alpha):</strong> Weight given to the auditory modality. Higher values indicate greater influence of auditory stimuli.</li>
            <li><strong>β (Beta):</strong> Weight given to the visual modality. Higher values indicate greater influence of visual stimuli.</li>
            <li><strong>λ (Lambda):</strong> Interaction term that represents the synergistic effect of combining auditory and visual information. Higher values indicate stronger multisensory integration.</li>
        </ul>

        <p>Note: In all formulas, P(RT ≤ t) represents the cumulative probability of a response occurring by time t, and Φ represents the cumulative distribution function of the standard normal distribution.</p>
        """

        # Create a custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Race Model Information")
        dialog.setGeometry(100, 100, 800, 600)  # Larger window size

        # Create a layout for the dialog
        layout = QVBoxLayout()

        # Create a QTextEdit widget to display the information
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(info_text)  # Set the text as HTML for formatting

        # Set a larger, more readable font
        font = QFont("Arial", 11)
        text_edit.setFont(font)

        # Add the QTextEdit to the layout
        layout.addWidget(text_edit)

        # Create a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        # Set the layout for the dialog
        dialog.setLayout(layout)

        # Show the dialog
        dialog.exec_()

    def store_figure_data(self, plot_type, data_dict):
        """Store figure data consistently for all plot types"""
        self.figure_data[plot_type] = data_dict
        self.current_figure_type = plot_type

    def _customize_axes(self, ax):
        # Remove top and right axes
        ax.spines['top'].set_visible(False)

        ax.spines['right'].set_visible(False)
        # Customize other plot aesthetics if needed

    def interpret_bayes_factor(self, bf10):
        """Interpret Bayes Factor based on common guidelines."""
        if bf10 > 100:
            return "Extreme evidence for H₁"
        elif bf10 > 30:
            return "Very strong evidence for H₁"
        elif bf10 > 10:
            return "Strong evidence for H₁"
        elif bf10 > 3:
            return "Moderate evidence for H₁"
        elif bf10 > 1:
            return "Anecdotal evidence for H₁"
        elif bf10 == 1:
            return "No evidence"
        elif bf10 > 1/3:
            return "Anecdotal evidence for H₀"
        elif bf10 > 1/10:
            return "Moderate evidence for H₀"
        elif bf10 > 1/30:
            return "Strong evidence for H₀"
        elif bf10 > 1/100:
            return "Very strong evidence for H₀"
        else:
            return "Extreme evidence for H₀"

    def undo_exclusions(self):
        """Restore all datasets to their original state before any exclusions."""
        total_excluded_trials = 0
        total_excluded_participants = 0
        
        # Process each dataset
        for dataset_name in self.datasets:
            # Calculate excluded trials
            current_data = self.datasets[dataset_name]["data"]
            original_data = self.datasets[dataset_name]["original_data"]
            excluded_trials = len(original_data) - len(current_data)
            total_excluded_trials += excluded_trials
            
            # Count excluded participants
            n_excluded_participants = len(self.excluded_participants.get(dataset_name, []))
            total_excluded_participants += n_excluded_participants
            
            # Restore original data
            self.datasets[dataset_name]["data"] = self.datasets[dataset_name]["original_data"].copy()
            
            # Clear exclusions for this dataset
            self.excluded_participants[dataset_name] = []
            self.excluded_trials[dataset_name] = []
        
        # Show detailed status message
        status_msg = f'Restored {total_excluded_trials} excluded trials'
        if total_excluded_participants > 0:
            status_msg += f' and {total_excluded_participants} excluded participants'
        self.statusBar().showMessage(status_msg, 5000)
        
        # Clear any exclusion-related displays
        self.outlier_report.setVisible(False)
        self.outlier_report.clear()
        
        # Refresh current plot if one exists
        if hasattr(self, 'current_figure_type'):
            if self.current_figure_type in ['mean_rts', 'median_rts', 'boxplot_rts', 
                                          'participant_distribution', 'race_model', 'scatter']:
                getattr(self, f'plot_{self.current_figure_type}')()

    def open_participant_selection_dialog(self):
        """Enhanced dialog for excluding participants with preview and save options"""
        selected_items = self.dataset_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return
            
        dataset_name = selected_items[0].text()
        if dataset_name not in self.datasets:
            return
            
        data = self.datasets[dataset_name]["data"]
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Exclude Participants - {dataset_name}")
        dialog.setMinimumSize(600, 800)
        main_layout = QVBoxLayout(dialog)
        
        # Create tabs for different exclusion methods
        tab_widget = QTabWidget()
        
        # Tab 1: Manual Selection
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        
        # Add current participant stats
        stats_label = QLabel()
        stats_text = f"Current Dataset Stats:\n"
        stats_text += f"Total Participants: {len(data['participant_number'].unique())}\n"
        for col in data.columns:
            if col.lower() in ['age', 'subjectage']:
                stats_text += f"Age Range: {data[col].min():.1f} - {data[col].max():.1f}\n"
        manual_layout.addWidget(stats_label)
        stats_label.setText(stats_text)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add checkboxes for each participant with demographic info
        participant_checkboxes = {}
        all_participants = sorted(data['participant_number'].unique())
        demo_cols = [col for col in data.columns if col.lower() in 
                    ['age', 'gender', 'sex', 'education', 'subjectage', 'subjectsex']]
        
        for participant in all_participants:
            participant_data = data[data['participant_number'] == participant].iloc[0]
            checkbox_text = f"Participant {participant}"
            
            # Add demographic info to checkbox label
            demo_info = []
            for col in demo_cols:
                value = participant_data[col]
                if pd.api.types.is_numeric_dtype(data[col]):
                    demo_info.append(f"{col}: {value:.1f}")
                else:
                    demo_info.append(f"{col}: {value}")
            
            if demo_info:
                checkbox_text += f" ({', '.join(demo_info)})"
                
            checkbox = QCheckBox(checkbox_text)
            if participant in self.excluded_participants.get(dataset_name, []):
                checkbox.setChecked(True)
            participant_checkboxes[participant] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll.setWidget(scroll_content)
        manual_layout.addWidget(scroll)
 
        
        tab_widget.addTab(manual_tab, "Manual Selection")
        
        # Tab 2: Demographic Criteria
        demo_tab = QWidget()
        demo_layout = QVBoxLayout(demo_tab)
        demo_form = QFormLayout()
        
        demographic_filters = {}
        
        for col in demo_cols:
            if pd.api.types.is_numeric_dtype(data[col]):
                # Numeric criteria (e.g., age)
                filter_widget = QWidget()
                filter_layout = QHBoxLayout(filter_widget)
                
                min_val = QLineEdit()
                max_val = QLineEdit()
                current_min = data[col].min()
                current_max = data[col].max()
                
                min_val.setPlaceholderText(f"Min ({current_min:.1f})")
                max_val.setPlaceholderText(f"Max ({current_max:.1f})")
                
                filter_layout.addWidget(QLabel("From:"))
                filter_layout.addWidget(min_val)
                filter_layout.addWidget(QLabel("To:"))
                filter_layout.addWidget(max_val)
                
                demographic_filters[col] = {
                    "type": "numeric",
                    "widgets": (min_val, max_val),
                    "range": (current_min, current_max)
                }
                
                demo_form.addRow(f"{col}:", filter_widget)
            else:
                # Categorical criteria (e.g., gender)
                filter_widget = QWidget()
                filter_layout = QVBoxLayout(filter_widget)
                
                unique_values = data[col].unique()
                checkboxes = []
                
                for value in unique_values:
                    if pd.notna(value):
                        checkbox = QCheckBox(str(value))
                        checkbox.setChecked(True)
                        checkboxes.append(checkbox)
                        filter_layout.addWidget(checkbox)
                
                demographic_filters[col] = {
                    "type": "categorical",
                    "widgets": checkboxes
                }
                
                demo_form.addRow(f"{col}:", filter_widget)
        
        demo_layout.addLayout(demo_form)
        tab_widget.addTab(demo_tab, "Demographic Criteria")
        main_layout.addWidget(tab_widget)
        
        # Preview button
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setMaximumHeight(150)
        preview_layout.addWidget(preview_text)
        main_layout.addWidget(preview_group)
        
        preview_button = QPushButton("Preview Exclusions")
        main_layout.addWidget(preview_button)
        
        def update_preview():
            excluded = set()
            
            # Manual exclusions
            manual_excluded = [p for p, cb in participant_checkboxes.items() if cb.isChecked()]
            excluded.update(manual_excluded)
            
            # Demographic exclusions
            for col, filter_info in demographic_filters.items():
                if filter_info["type"] == "numeric":
                    min_widget, max_widget = filter_info["widgets"]
                    try:
                        min_val = float(min_widget.text()) if min_widget.text() else None
                        max_val = float(max_widget.text()) if max_widget.text() else None
                        
                        if min_val is not None:
                            excluded.update(data[data[col] < min_val]['participant_number'])
                        if max_val is not None:
                            excluded.update(data[data[col] > max_val]['participant_number'])
                    except ValueError:
                        pass
                else:  # categorical
                    selected_values = [cb.text() for cb in filter_info["widgets"] if cb.isChecked()]
                    if selected_values:
                        excluded.update(data[~data[col].isin(selected_values)]['participant_number'])
            
            # Update preview text
            preview = "Exclusion Summary:\n"
            preview += f"Total participants to exclude: {len(excluded)}\n"
            preview += f"Remaining participants: {len(all_participants) - len(excluded)}\n\n"
            
            if excluded:
                preview += "Participants to be excluded:\n"
                for participant in sorted(excluded):
                    participant_info = "P{:d}".format(participant)
                    # Add demographic info for each participant
                    participant_data = data[data['participant_number'] == participant].iloc[0]
                    for col in demo_cols:
                        value = participant_data[col]
                        if pd.api.types.is_numeric_dtype(data[col]):
                            participant_info += f" | {col}: {value:.1f}"
                        else:
                            participant_info += f" | {col}: {value}"
                    preview += participant_info + "\n"
                
                # Add demographic summary
                if demo_cols:
                    preview += "\nDemographic summary of excluded participants:\n"
                    excluded_data = data[data['participant_number'].isin(excluded)]
                    for col in demo_cols:
                        if pd.api.types.is_numeric_dtype(data[col]):
                            preview += f"{col}: {excluded_data[col].mean():.1f} ± {excluded_data[col].std():.1f}\n"
                        else:
                            value_counts = excluded_data[col].value_counts()
                            preview += f"{col}: {dict(value_counts)}\n"
            
            
            preview_text.setText(preview)
        
        preview_button.clicked.connect(update_preview)
        
        # Add save options
        save_options = QGroupBox("Save Options")
        save_layout = QHBoxLayout(save_options)
        save_checkbox = QCheckBox("Save as new dataset")
        save_name = QLineEdit()
        save_name.setPlaceholderText("Enter new dataset name")
        save_name.setEnabled(False)
        save_checkbox.toggled.connect(save_name.setEnabled)
        save_layout.addWidget(save_checkbox)
        save_layout.addWidget(save_name)
        main_layout.addWidget(save_options)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply Exclusions")
        cancel_button = QPushButton("Cancel")
        
        def apply_exclusions():
            excluded = set()
            
            # Get manual exclusions
            manual_excluded = [p for p, cb in participant_checkboxes.items() if cb.isChecked()]
            excluded.update(manual_excluded)
            
            # Get demographic exclusions
            for col, filter_info in demographic_filters.items():
                if filter_info["type"] == "numeric":
                    min_widget, max_widget = filter_info["widgets"]
                    try:
                        min_val = float(min_widget.text()) if min_widget.text() else None
                        max_val = float(max_widget.text()) if max_widget.text() else None
                        
                        if min_val is not None:
                            excluded.update(data[data[col] < min_val]['participant_number'])
                        if max_val is not None:
                            excluded.update(data[data[col] > max_val]['participant_number'])
                    except ValueError:
                        pass
                else:  # categorical
                    selected_values = [cb.text() for cb in filter_info["widgets"] if cb.isChecked()]
                    if selected_values:
                        excluded.update(data[~data[col].isin(selected_values)]['participant_number'])
            
            if save_checkbox.isChecked() and save_name.text():
                # Create new dataset with exclusions
                new_name = save_name.text()
                if new_name in self.datasets:
                    QMessageBox.warning(dialog, "Name Exists", 
                                      "A dataset with this name already exists.")
                    return
                    
                # Create filtered dataset
                new_data = data[~data['participant_number'].isin(excluded)].copy()
                color = plt.cm.tab20(len(self.datasets) % 20)
                pattern = 'solid'
                
                self.datasets[new_name] = {
                    "data": new_data,
                    "original_data": new_data.copy(),
                    "color": color,
                    "pattern": pattern
                }
                self.dataset_list.addItem(new_name)
                self.dataset_colors[new_name] = color
                self.dataset_patterns[new_name] = pattern
                self.excluded_participants[new_name] = []
                self.excluded_trials[new_name] = []
            else:
                # Apply exclusions to existing dataset
                self.excluded_participants[dataset_name] = list(excluded)
            
            self.update_plots()
            dialog.accept()
            
        ok_button.clicked.connect(apply_exclusions)
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        # Initial preview
        update_preview()
        
        dialog.exec_()

    def update_plots(self):
        # Update the current plot with new participant selection
        if self.current_figure_type == 'mean_rts':
            self.plot_mean_rts()
        elif self.current_figure_type == 'median_rts':
            self.plot_median_rts()
        elif self.current_figure_type == 'boxplot_rts':
            self.plot_boxplot_rts()
        elif self.current_figure_type == 'participant_distribution':
            self.plot_participant_distribution()
        elif self.current_figure_type == 'race_model':
            self.plot_race_model()
        elif self.current_figure_type == 'scatter_plot':
            self.plot_scatter()

    def load_dataset(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", 
                                              "CSV Files (*.csv);;All Files (*)", 
                                              options=options)
        if file_path:
            dialog = QDialog(self)
            dialog.setWindowTitle("Dataset Properties")
            layout = QFormLayout(dialog)
            
            # Dataset name input
            name_input = QLineEdit(os.path.basename(file_path))
            layout.addRow("Dataset Name:", name_input)
            
            # Pattern selector
            pattern_selector = QComboBox()
            patterns = ['solid', 'clear', 'hatched', 'dotted', 'dashed', 'cross-hatched']
            pattern_descriptions = {
                'solid': 'Solid fill',
                'clear': 'Outline only',
                'hatched': 'Diagonal lines (///)',
                'dotted': 'Dotted pattern (...)',
                'dashed': 'Dashed lines (---)',
                'cross-hatched': 'Cross-hatched pattern (xxx)'
            }
            for pattern in patterns:
                pattern_selector.addItem(f"{pattern} - {pattern_descriptions[pattern]}", pattern)
            layout.addRow("Bar Pattern:", pattern_selector)
            
            # Transparency slider
            alpha_slider = QSlider(Qt.Horizontal)
            alpha_slider.setRange(1, 100)
            alpha_slider.setValue(100)
            alpha_label = QLabel("100%")
            alpha_slider.valueChanged.connect(lambda v: alpha_label.setText(f"{v}%"))
            
            alpha_layout = QHBoxLayout()
            alpha_layout.addWidget(alpha_slider)
            alpha_layout.addWidget(alpha_label)
            layout.addRow("Opacity:", alpha_layout)
            
            # Preview canvas
            preview_figure = plt.figure(figsize=(3, 2))
            preview_canvas = FigureCanvas(preview_figure)
            preview_canvas.setFixedSize(200, 150)
            layout.addRow("Preview:", preview_canvas)
            
            def update_preview():
                preview_figure.clear()
                ax = preview_figure.add_subplot(111)
                
                pattern = pattern_selector.currentData()
                alpha = alpha_slider.value() / 100.0
                
                # Create sample bars with different modalities
                x = [0, 1, 2]
                heights = [0.7, 0.8, 0.6]
                colors = ['red', 'blue', 'purple']
                labels = ['Audio', 'Visual', 'AV']
                
                for i, (height, color, label) in enumerate(zip(heights, colors, labels)):
                    bar = ax.bar(x[i], height, width=0.8, 
                                color='white' if pattern != 'solid' else color,
                                edgecolor=color,
                                alpha=alpha,
                                label=label)
                    
                    # Apply pattern
                    if pattern == 'hatched':
                        bar[0].set_hatch('///')
                    elif pattern == 'dotted':
                        bar[0].set_hatch('...')
                    elif pattern == 'dashed':
                        bar[0].set_hatch('--')
                    elif pattern == 'cross-hatched':
                        bar[0].set_hatch('xxx')
                
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=45)
                ax.set_ylim(0, 1)
                ax.set_title('Preview', fontsize=8)
                
                # Remove spines and ticks for cleaner look
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                preview_figure.tight_layout()
                preview_canvas.draw()
            
            # Connect preview updates to changes in pattern and alpha
            pattern_selector.currentIndexChanged.connect(update_preview)
            alpha_slider.valueChanged.connect(update_preview)
            
            # Initial preview
            update_preview()
            
            # Dialog buttons
            button_box = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            button_box.addWidget(ok_button)
            button_box.addWidget(cancel_button)
            layout.addRow(button_box)
            
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            if dialog.exec_() == QDialog.Accepted:
                name = name_input.text()
                if name in self.datasets:
                    QMessageBox.warning(self, "Name Exists", 
                                      "A dataset with this name already exists.")
                    return
                
                try:
                    data = pd.read_csv(file_path)
                    color = plt.cm.tab20(len(self.datasets) % 20)
                    
                    # Get selected pattern and alpha
                    pattern = pattern_selector.currentData()
                    alpha = alpha_slider.value() / 100.0
                    
                    # Store both original and working copy of data with appearance properties
                    self.datasets[name] = {
                        "data": data.copy(),
                        "original_data": data.copy(),
                        "color": color,
                        "pattern": pattern,
                        "alpha": alpha
                    }
                    
                    self.dataset_list.addItem(name)
                    self.dataset_colors[name] = color
                    self.dataset_patterns[name] = pattern
                    
                    # Initialize empty exclusion lists for this dataset
                    self.excluded_participants[name] = []
                    self.excluded_trials[name] = []
                    
                    # Update participant selector
                    self.update_participant_selector()
                    self.statusBar().showMessage(f'Loaded dataset: {name}')
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load dataset: {str(e)}")
    def combine_datasets(self):
        """Combine selected datasets into a single dataset"""
        selected_items = self.dataset_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, "Selection Error", 
                              "Please select at least two datasets to combine.")
            return
    
        # Get name for combined dataset
        name, ok = QInputDialog.getText(self, 'Combined Dataset Name', 
                                      'Enter a name for the combined dataset:',
                                      text='Combined_Dataset')
        if not ok or not name:
            return
        
        if name in self.datasets:
            QMessageBox.warning(self, "Name Exists", 
                              "A dataset with this name already exists.")
            return
    
        try:
            # Combine the selected datasets
            combined_data = pd.DataFrame()
            for item in selected_items:
                dataset_name = item.text()
                data = self.datasets[dataset_name]["data"].copy()
                # Add a column to identify original dataset
                data['source_dataset'] = dataset_name
                combined_data = pd.concat([combined_data, data], ignore_index=True)
    
            # Store the combined dataset
            color = plt.cm.tab20(len(self.datasets) % 20)
            pattern = 'solid'  # You can adjust the pattern as needed
            
            self.datasets[name] = {
                "data": combined_data.copy(),
                "original_data": combined_data.copy(),
                "color": color,
                "pattern": pattern
            }
            
            # Add to list and initialize exclusions
            self.dataset_list.addItem(name)
            self.dataset_colors[name] = color
            self.dataset_patterns[name] = pattern
            self.excluded_participants[name] = []
            self.excluded_trials[name] = []
            
            # Update participant selector
            self.update_participant_selector()
            
            QMessageBox.information(self, "Success", 
                                  f"Successfully combined {len(selected_items)} datasets into '{name}'")
            self.statusBar().showMessage(f'Created combined dataset: {name}')
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to combine datasets: {str(e)}")

    def open_csv_for_formatting(self):
        options = QFileDialog.Options()
        # Allow both CSV and Excel files
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File to Format", "",
                                                "Data Files (*.csv *.xlsx *.xls);;All Files (*)",
                                                options=options)
        if file_path:
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()

            try:
                if file_ext in ['.xlsx', '.xls']:
                    # It's an Excel file, load the file and ask user which sheet to use
                    xls = pd.ExcelFile(file_path)
                    sheets = xls.sheet_names

                    # If there's more than one sheet, ask the user to select one
                    if len(sheets) > 1:
                        sheet_name, ok = QInputDialog.getItem(self, 
                                                            "Select Sheet", 
                                                            "Multiple sheets found. Select one:", 
                                                            sheets, 0, False)
                        if not ok:
                            return
                    else:
                        sheet_name = sheets[0]

                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    # Assume CSV
                    df = pd.read_csv(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")
                return
            
            required_columns = ["participant_number", "modality", "reaction_time"]

            # Dialog to map columns
            dialog = QDialog(self)
            dialog.setWindowTitle("Map Columns for Formatting")
            dialog_layout = QVBoxLayout(dialog)
            
            form_layout = QFormLayout()
            combo_boxes = {}
            csv_columns = df.columns.tolist()
            for req_col in required_columns:
                combo = QComboBox()
                combo.addItems(csv_columns)
                form_layout.addRow(f"Map {req_col}:", combo)
                combo_boxes[req_col] = combo
            
            dialog_layout.addLayout(form_layout)
            
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            dialog_layout.addLayout(button_layout)
            
            def apply_mapping():
                mapping = {req: combo_boxes[req].currentText() for req in required_columns}
                success = self.format_csv_file(df, mapping)
                if success:
                    QMessageBox.information(dialog, "Success", "File formatted and saved as CSV successfully.")
                    dialog.accept()
            
            ok_button.clicked.connect(apply_mapping)
            cancel_button.clicked.connect(dialog.reject)
            
            dialog.exec_()


    def format_csv_file(self, df, mapping):
        # Helper function to perform the actual CSV formatting
        required_columns = ["participant_number", "modality", "reaction_time"]
        try:
            df_formatted = df[[mapping[col] for col in required_columns]].copy()
            df_formatted.columns = required_columns
            
            # Ensure proper data types if needed
            df_formatted['participant_number'] = pd.to_numeric(df_formatted['participant_number'], errors='coerce').fillna(0).astype(int)
            df_formatted['modality'] = pd.to_numeric(df_formatted['modality'], errors='coerce').fillna(1).astype(int)
            df_formatted['reaction_time'] = pd.to_numeric(df_formatted['reaction_time'], errors='coerce').fillna(0).astype(float)
            
            options = QFileDialog.Options()
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Formatted CSV", "", 
                                                    "CSV Files (*.csv);;All Files (*)", 
                                                    options=options)
            if save_path:
                if not save_path.lower().endswith('.csv'):
                    save_path += '.csv'
                df_formatted.to_csv(save_path, index=False)
                return True
            else:
                return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to format CSV: {str(e)}")
            return False

    def calculate_between_dataset_statistics(self, selected_items):
        """Calculate statistical comparisons between datasets"""
        stats_text = "Between-Dataset Statistics:\n\n"
        
        for modality, mod_name in [(1, "Audio"), (2, "Visual"), (3, "Audiovisual")]:
            stats_text += f"{mod_name} Modality:\n"
            
            # Compare each pair of datasets
            for i in range(len(selected_items)):
                for j in range(i + 1, len(selected_items)):
                    name1 = selected_items[i].text()
                    name2 = selected_items[j].text()
                    
                    data1 = self.datasets[name1]["data"]
                    data2 = self.datasets[name2]["data"]
                    
                    rt1 = data1[data1['modality'] == modality]['reaction_time']
                    rt2 = data2[data2['modality'] == modality]['reaction_time']
                    
                    if self.ttest_radio.isChecked():
                        t_stat, p_val = ttest_ind(rt1, rt2)
                        stats_text += f"{name1} vs {name2}: "
                        stats_text += f"t = {t_stat:.2f}, p = {p_val:.4f}\n"
                    else:
                        t_stat, _ = ttest_ind(rt1, rt2)
                        bf10 = bayesfactor_ttest(t=t_stat, nx=len(rt1), ny=len(rt2))
                        # Format BF10 to scientific notation if > 1000
                        if abs(bf10) >= 1000:
                            stats_text += f"{name1} vs {name2}: BF₁₀ = {bf10:.2e}\n"
                        else:
                            stats_text += f"{name1} vs {name2}: BF₁₀ = {bf10:.2f}\n"
            
            stats_text += "\n"
        
        return stats_text

    def adjust_lightness(self, color, alpha):
        """Adjust the lightness of a color based on alpha"""
        rgb = mcolors.to_rgb(color)
        # Mix with white based on alpha
        return tuple(c * alpha + (1 - alpha) for c in rgb)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ReactionTimeAnalysisGUI()
    sys.exit(app.exec_())
