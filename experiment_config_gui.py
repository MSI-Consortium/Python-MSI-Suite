import sys
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, 
                             QLabel, QLineEdit, QSpinBox, QComboBox, QGroupBox, QFormLayout, QCheckBox, QScrollArea, QDoubleSpinBox)
import os
import subprocess
import redcap
from typing import List
import copy

class BlockConfig(QGroupBox):
    def __init__(self, block_number):
        super().__init__(f"Block {block_number}")
        self.block_number = block_number
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.exp_type = QComboBox()
        self.exp_type.addItems(['SJ', 'SRT', 'SRT_Mod', 'SJ_Mod'])
        self.exp_type.currentTextChanged.connect(self.on_experiment_change)
        layout.addRow('Experiment Type:', self.exp_type)

        self.trials_per_condition = QSpinBox()
        self.trials_per_condition.setRange(1, 100)
        self.trials_per_condition.valueChanged.connect(self.update_estimates)
        layout.addRow('Trials per condition:', self.trials_per_condition)

        self.left_audio_high = QCheckBox('Left audio high pitch')
        self.left_audio_high.hide()
        layout.addRow(self.left_audio_high)

        self.left_visual_green = QCheckBox('Left visual green')
        self.left_visual_green.hide()
        layout.addRow(self.left_visual_green)

        self.total_trials_label = QLabel('Total trials: 0')
        layout.addRow(self.total_trials_label)

        self.time_estimate_label = QLabel('Estimated time: 0 min')
        layout.addRow(self.time_estimate_label)

        self.setLayout(layout)
        self.on_experiment_change('SJ')

    def on_experiment_change(self, exp_type):
        self.left_audio_high.setVisible(exp_type == 'SRT_Mod')
        self.left_visual_green.setVisible(exp_type == 'SRT_Mod')
        self.update_estimates()

    def update_estimates(self):
        exp_type = self.exp_type.currentText()
        trials_per_condition = self.trials_per_condition.value()
        total_trials = 0
        estimated_time = 0

        if exp_type == 'SJ':
            total_trials = trials_per_condition * 13  # 13 SOA conditions
            estimated_time = total_trials * (2 + 0.05)  # 2s ITI + 50ms stimulus
        elif exp_type == 'SRT':
            total_trials = trials_per_condition * 3  # 3 conditions
            estimated_time = total_trials * (1.5 + 0.05)  # 1-2s ITI (avg 1.5s) + 50ms stimulus
        elif exp_type == 'SRT_Mod':
            total_trials = trials_per_condition * 9  # 9 trial types
            estimated_time = total_trials * (1.5 + 0.05)  # 1-2s ITI (avg 1.5s) + 50ms stimulus
        elif exp_type == 'SJ_Mod':
            total_trials = trials_per_condition * 9 * 6  # 9 SOAs, 6 conditions
            estimated_time = total_trials * (2 + 0.05)  # 2s ITI + 50ms stimulus

        self.total_trials_label.setText(f'Total trials: {total_trials}')
        self.time_estimate_label.setText(f'Estimated time: {estimated_time/60:.1f} min')

    def get_config(self):
        config = {
            'experiment': self.exp_type.currentText(),
            'block_number': self.block_number,
            'trials_per_condition': self.trials_per_condition.value(),
            'total_trials': int(self.total_trials_label.text().split(': ')[1]),
            'estimated_time': float(self.time_estimate_label.text().split(': ')[1].split(' ')[0])
        }

        if self.exp_type.currentText() == 'SRT_Mod':
            config['left_audio_high'] = self.left_audio_high.isChecked()
            config['left_visual_green'] = self.left_visual_green.isChecked()

        return config

class ExperimentConfigApp(QWidget):
    def update_participant_ids(self):
        """Update participant ID combo box with existing records and next available ID."""
        try:
            existing_ids = self.fetch_redcap_records()
            
            # Clear current items
            self.participant_id.clear()
            
            # Format existing IDs with leading zeros
            formatted_ids = [str(int(id)).zfill(3) for id in existing_ids]
            
            # Add formatted existing IDs
            self.participant_id.addItems(formatted_ids)
            
            # Calculate and add next available ID with leading zeros
            if existing_ids:
                next_id = str(int(max(existing_ids)) + 1).zfill(3)
            else:
                next_id = "001"
                
            self.participant_id.addItem(next_id)
            self.participant_id.setCurrentText(next_id)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update participant IDs: {str(e)}")
    
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.last_saved_file = None
        self.original_config = None  # Store the original config for change detection
        self.has_unsaved_changes = False  # Track whether changes have been made
        
        self.initUI()
        self.load_default_config()
        self.load_api_credentials()
        
        # Connect API credential changes to participant ID update
        self.api_url.textChanged.connect(self.update_participant_ids)
        self.api_token.textChanged.connect(self.update_participant_ids)
        
        # Connect change tracking to all input widgets
        self.connect_change_tracking()

    def initUI(self):
        self.setWindowTitle('Multi-Block Experiment Configuration')
        self.setGeometry(100, 100, 800, 800)
        
        main_layout = QVBoxLayout()
    
        # Create participant group
        participant_group = QGroupBox('Participant Information')
        participant_layout = QFormLayout()
    
        # Participant ID setup
        self.participant_id = QComboBox()
        self.participant_id.setEditable(True)
        self.participant_id.setInsertPolicy(QComboBox.InsertPolicy.InsertAlphabetically)
        self.refresh_participant_id_button = QPushButton("Refresh IDs")
        self.refresh_participant_id_button.clicked.connect(self.update_participant_ids)
    
        participant_id_layout = QHBoxLayout()
        participant_id_layout.addWidget(self.participant_id)
        participant_id_layout.addWidget(self.refresh_participant_id_button)
    
        # Other participant fields
        self.age = QSpinBox()
        self.age.setRange(4, 100)
        self.gender = QComboBox()
        self.gender.addItems(['m', 'f'])
        self.site = QComboBox()
        self.site.addItems(['vandy', 'yale', 'iit', 'chuv'])
    
        # Add fullscreen checkbox after site selection
        self.fullscreen = QCheckBox('Fullscreen Mode')
        participant_layout.addRow('Fullscreen:', self.fullscreen)
        
        # Add test mode checkbox for SJ tasks
        self.test_mode = QCheckBox('Test Mode (show SOA values)')
        participant_layout.addRow('Test Mode:', self.test_mode)
        
        # Add offline mode checkbox
        self.offline_mode = QCheckBox('Offline Mode (no REDCap connection required)')
        participant_layout.addRow('Offline Mode:', self.offline_mode)
        
        # API URL and Token input fields
        self.api_url = QLineEdit()
        self.api_token = QLineEdit()
        self.api_token.setEchoMode(QLineEdit.Password)  # Hide API token for security
    
        # Add widgets to participant layout
        participant_layout.addRow('Participant ID:', participant_id_layout)
        participant_layout.addRow('Age:', self.age)
        participant_layout.addRow('Gender:', self.gender)
        participant_layout.addRow('Site:', self.site)
        participant_layout.addRow('API URL:', self.api_url)
        participant_layout.addRow('API Token:', self.api_token)
        
        participant_group.setLayout(participant_layout)
        main_layout.addWidget(participant_group)

        # Audiovisual Synchrony Correction
        av_sync_group = QGroupBox('Audiovisual Synchrony Correction')
        av_sync_layout = QFormLayout()

        self.av_sync_correction = QDoubleSpinBox()
        self.av_sync_correction.setRange(-1000, 1000)  # Range in milliseconds
        self.av_sync_correction.setSingleStep(1)
        self.av_sync_correction.setDecimals(0)
        self.av_sync_correction.setSingleStep(1)
        self.av_sync_correction.setSuffix(' ms')
        self.av_sync_correction.setDecimals(2)
        
        # Add tooltip explanation for correction factor
        self.av_sync_correction.setToolTip(
            "Positive values move the visual stimulus earlier (forward) in relation to audio.\n"
            "Negative values move the visual stimulus later (backward) in relation to audio.\n"
            "Example: +100ms means visual appears 100ms before audio would normally occur."
        )
        
        # Add explanatory label for correction factor
        correction_explanation = QLabel(
            "Positive: Visual comes earlier, Negative: Visual comes later"
        )
        correction_explanation.setWordWrap(True)

        av_sync_layout.addRow('Correction (ms):', self.av_sync_correction)
        av_sync_layout.addRow(correction_explanation)
        av_sync_group.setLayout(av_sync_layout)
        main_layout.addWidget(av_sync_group)

        # Blocks area
        self.blocks_scroll = QScrollArea()
        self.blocks_scroll.setWidgetResizable(True)
        self.blocks_widget = QWidget()
        self.blocks_layout = QHBoxLayout(self.blocks_widget)
        self.blocks_scroll.setWidget(self.blocks_widget)
        main_layout.addWidget(self.blocks_scroll)

        # Add/Remove block buttons
        button_layout = QHBoxLayout()
        add_block_button = QPushButton('Add Block')
        add_block_button.clicked.connect(self.add_block)
        button_layout.addWidget(add_block_button)
        remove_block_button = QPushButton('Remove Last Block')
        remove_block_button.clicked.connect(self.remove_block)
        button_layout.addWidget(remove_block_button)
        main_layout.addLayout(button_layout)

        # Total experiment time estimate
        self.total_time_label = QLabel('Total estimated experiment time: 0 min')
        main_layout.addWidget(self.total_time_label)

        # Status label for change tracking
        self.status_label = QLabel('')  # Initialized empty
        main_layout.addWidget(self.status_label)

        # Load, Save and Run buttons
        load_save_run_layout = QHBoxLayout()
        
        self.load_button = QPushButton('Load Configuration')
        self.load_button.clicked.connect(self.load_config_file)
        load_save_run_layout.addWidget(self.load_button)
        
        self.save_button = QPushButton('Save Configuration')
        self.save_button.clicked.connect(self.save_config)
        load_save_run_layout.addWidget(self.save_button)
        
        self.run_button = QPushButton('Save and Run Experiment')
        self.run_button.clicked.connect(self.save_and_run)
        load_save_run_layout.addWidget(self.run_button)
        
        main_layout.addLayout(load_save_run_layout)

        self.setLayout(main_layout)
        self.add_block()  # Start with one block

    def connect_change_tracking(self):
        """Connect change tracking signals to all UI elements"""
        # Connect participant info widgets
        self.participant_id.currentTextChanged.connect(self.mark_as_changed)
        self.participant_id.editTextChanged.connect(self.mark_as_changed)
        self.age.valueChanged.connect(self.mark_as_changed)
        self.gender.currentTextChanged.connect(self.mark_as_changed)
        self.site.currentTextChanged.connect(self.mark_as_changed)
        self.fullscreen.stateChanged.connect(self.mark_as_changed)
        self.test_mode.stateChanged.connect(self.mark_as_changed)
        self.offline_mode.stateChanged.connect(self.mark_as_changed)
        self.api_url.textChanged.connect(self.mark_as_changed)
        self.api_token.textChanged.connect(self.mark_as_changed)
        self.av_sync_correction.valueChanged.connect(self.mark_as_changed)
        
        # Block add/remove actions are connected separately in their respective methods

    def mark_as_changed(self):
        """Mark the configuration as having unsaved changes"""
        self.has_unsaved_changes = True
        self.update_status_label()
    
    def update_status_label(self):
        """Update the status label to reflect current change state"""
        if self.has_unsaved_changes:
            self.status_label.setText("<b>Unsaved changes</b>")
        else:
            self.status_label.setText("")

    def fetch_redcap_records(self) -> List[str]:
        """Fetch existing record IDs from REDCap and determine next available ID."""
        try:
            if not self.api_url.text() or not self.api_token.text():
                return []
            
            project = redcap.Project(self.api_url.text(), self.api_token.text())
            records = project.export_records(fields=['record_id'])
            record_ids = [str(record['record_id']) for record in records]
            return sorted(record_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
        except Exception as e:
            QMessageBox.warning(self, "REDCap Connection Error", f"Could not fetch records: {str(e)}")
            return []
    
    def load_default_config(self):
        default_file = 'default.json'
        if os.path.exists(default_file):
            self.load_config_from_file(default_file, set_last_saved_file=False)
            self.has_unsaved_changes = False  # Reset change tracker after loading default
            self.update_status_label()

    def load_config_file(self):
        # Check for unsaved changes before loading a new config
        if self.has_unsaved_changes:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                                      'You have unsaved changes. Do you want to save them first?',
                                      QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                if not self.save_config():
                    return  # User canceled save operation
            elif reply == QMessageBox.Cancel:
                return  # User canceled the load operation
        
        filename, _ = QFileDialog.getOpenFileName(self, 'Load Config', '', 'JSON Files (*.json)')
        if filename:
            self.load_config_from_file(filename)

    def load_config_from_file(self, filename, set_last_saved_file=True):
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            
            # Store a deep copy of the original config for change comparison
            self.original_config = copy.deepcopy(config)
            
            self.load_config(config)
            QMessageBox.information(self, "Configuration Loaded", f"Configuration loaded from {filename}")
            
            if set_last_saved_file:
                self.last_saved_file = filename
            
            # Reset change tracking after loading
            self.has_unsaved_changes = False
            self.update_status_label()
            
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", "Invalid JSON file. Please select a valid configuration file.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred while loading the file: {str(e)}")

    def load_config(self, config):
        # Change setText to setCurrentText for QComboBox
        self.participant_id.setCurrentText(str(config.get('participant_id', '')))
        self.age.setValue(config.get('age', 0))
        self.gender.setCurrentText(config.get('gender', 'm'))
        self.site.setCurrentText(config.get('site', 'vandy'))
        self.fullscreen.setChecked(config.get('fullscreen', False))  # Load fullscreen setting
        self.test_mode.setChecked(config.get('test_mode', False))  # Load test mode setting
        self.offline_mode.setChecked(config.get('offline_mode', False))  # Load offline mode setting
    
        # Set audiovisual synchrony correction value
        self.av_sync_correction.setValue(config.get('av_sync_correction', 0.0))
    
        # Clear existing blocks
        for block in self.blocks:
            block.setParent(None)
            block.deleteLater()
        self.blocks.clear()
    
        # Add blocks from config
        for block_config in config.get('blocks', []):
            self.add_block(block_config)
    
        self.update_total_time()

    def add_block(self, block_config=None):
        block = BlockConfig(len(self.blocks) + 1)
        block.trials_per_condition.valueChanged.connect(self.update_total_time)
        block.exp_type.currentTextChanged.connect(self.update_total_time)
        
        # Connect change tracking to block widgets
        block.trials_per_condition.valueChanged.connect(self.mark_as_changed)
        block.exp_type.currentTextChanged.connect(self.mark_as_changed)
        block.left_audio_high.stateChanged.connect(self.mark_as_changed)
        block.left_visual_green.stateChanged.connect(self.mark_as_changed)
        
        if block_config:
            block.exp_type.setCurrentText(block_config.get('experiment', 'SJ'))
            block.trials_per_condition.setValue(block_config.get('trials_per_condition', 1))
            if block_config.get('experiment') == 'SRT_Mod':
                block.left_audio_high.setChecked(block_config.get('left_audio_high', False))
                block.left_visual_green.setChecked(block_config.get('left_visual_green', False))
        
        self.blocks.append(block)
        self.blocks_layout.addWidget(block)
        self.update_total_time()
        
        # Mark as changed if this was a user-initiated block addition (not from loading)
        if not block_config:
            self.mark_as_changed()

    def remove_block(self):
        if self.blocks:
            block = self.blocks.pop()
            block.setParent(None)
            block.deleteLater()
            self.update_total_time()
            # Mark as changed for user-initiated block removal
            self.mark_as_changed()

    def update_total_time(self):
        total_time = sum(float(block.time_estimate_label.text().split(': ')[1].split(' ')[0]) for block in self.blocks)
        self.total_time_label.setText(f'Total estimated experiment time: {total_time:.1f} min')

    def get_current_config(self):
        config = {
            'participant_id': self.participant_id.currentText(),  # Changed from text() to currentText()
            'age': self.age.value(),
            'gender': self.gender.currentText(),
            'site': self.site.currentText(),
            'fullscreen': self.fullscreen.isChecked(),  # Add fullscreen to config
            'test_mode': self.test_mode.isChecked(),  # Add test mode to config
            'offline_mode': self.offline_mode.isChecked(),  # Add offline mode to config
            'api_url': self.api_url.text(),
            'api_token': self.api_token.text(),
            'av_sync_correction': self.av_sync_correction.value(),  # Added missing field
            'blocks': [block.get_config() for block in self.blocks],
            'total_estimated_time': float(self.total_time_label.text().split(': ')[1].split(' ')[0])
        }
        return config
    
    def config_has_changed(self):
        """Compare current config with original loaded config to detect changes"""
        if self.original_config is None:
            return self.has_unsaved_changes
        
        current_config = self.get_current_config()
        
        # Remove API credential fields from comparison since they're saved separately
        current_copy = copy.deepcopy(current_config)
        original_copy = copy.deepcopy(self.original_config)
        
        if 'api_url' in current_copy:
            del current_copy['api_url']
        if 'api_token' in current_copy:
            del current_copy['api_token']
        if 'api_url' in original_copy:
            del original_copy['api_url']
        if 'api_token' in original_copy:
            del original_copy['api_token']
        
        return current_copy != original_copy
    
    def load_api_credentials(self, filename="api_text.txt"):
        """Load API URL and token from file, or prompt user if file is missing or values are invalid."""
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                for line in file:
                    key, value = line.strip().split('=')
                    if key == 'api_url':
                        self.api_url.setText(value)
                    elif key == 'api_token':
                        self.api_token.setText(value)
            # Update participant IDs after loading credentials
            self.update_participant_ids()
        else:
            QMessageBox.information(self, "Enter API Credentials", 
                                "API credentials not found. Please enter the API URL and Token in the fields provided.")
    
    def save_api_credentials(self, filename="api_text.txt"):
        """Save API URL and token to file."""
        with open(filename, 'w') as file:
            file.write(f"api_url={self.api_url.text()}\n")
            file.write(f"api_token={self.api_token.text()}\n")

    def save_config(self):
        config = self.get_current_config()
        
        # If we have a last_saved_file and no changes, no need to save again
        if self.last_saved_file and not self.has_unsaved_changes and not self.config_has_changed():
            return self.last_saved_file
        
        # If config has been modified, suggest saving with a new name
        suggest_new_filename = self.last_saved_file and self.config_has_changed()
        
        if suggest_new_filename:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("Configuration has been modified.")
            msg.setInformativeText("Do you want to save changes to a new file?")
            msg.setWindowTitle("Save Changes")
            save_new_btn = msg.addButton("Save As New", QMessageBox.ActionRole)
            overwrite_btn = msg.addButton("Overwrite Original", QMessageBox.ActionRole)
            cancel_btn = msg.addButton(QMessageBox.Cancel)
            msg.setDefaultButton(save_new_btn)
            msg.exec_()
            
            if msg.clickedButton() == save_new_btn:
                # User chose to save as new file - continue to file dialog
                pass
            elif msg.clickedButton() == overwrite_btn:
                # User chose to overwrite original file
                filename = self.last_saved_file
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Configuration Saved", f"Configuration saved to {filename}")
                self.original_config = copy.deepcopy(config)
                self.has_unsaved_changes = False
                self.update_status_label()
                self.save_api_credentials()
                return filename
            else:
                # User canceled
                return None
        
        # Default save dialog
        suggested_name = ''
        if self.last_saved_file and not suggest_new_filename:
            suggested_name = self.last_saved_file
            
        filename, _ = QFileDialog.getSaveFileName(self, 'Save Config', suggested_name, 'JSON Files (*.json)')
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            QMessageBox.information(self, "Configuration Saved", f"Configuration saved to {filename}")
            self.last_saved_file = filename
            self.original_config = copy.deepcopy(config)
            self.has_unsaved_changes = False
            self.update_status_label()
            self.save_api_credentials()  # Save API credentials when saving configuration
            return filename
        else:
            return None


    def save_and_run(self):
        # First, check if there are unsaved changes
        if self.has_unsaved_changes or self.config_has_changed():
            filename = self.save_config()
            if not filename:
                # User cancelled save, do not proceed
                QMessageBox.warning(self, "Save Configuration", "You must save the configuration before running the experiment.")
                return  # Exit the method without running the experiment
                
            self.last_saved_file = filename
        elif not self.last_saved_file:
            # No last saved file but no changes either - need to save first
            filename = self.save_config()
            if not filename:
                QMessageBox.warning(self, "Save Configuration", "You must save the configuration before running the experiment.")
                return
                
            self.last_saved_file = filename
        
        # Now we have a valid saved file that matches the current configuration
        
        # Proceed to run the experiment
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("The experiment will now start in a separate process.\n"
                    "This window will close to avoid interference with timing.\n"
                    "The experiment will run in the background.")
        msg.setWindowTitle("Starting Experiment")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

        # Start the experiment in a separate process
        subprocess.Popen([sys.executable, 'run_MSI_GUI_experiment.py', self.last_saved_file])

        # Close the configuration app
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ExperimentConfigApp()
    ex.show()
    sys.exit(app.exec_())