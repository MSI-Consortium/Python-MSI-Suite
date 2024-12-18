# Python MSI Suite
This repository contains a Python-based application for running customized multi-block psychophysical experiments. The experiments are designed to measure sensory processing and reaction times under various audiovisual conditions. The application provides a GUI for configuring experiments and supports data collection and integration with REDCap for data management.

<!-- ![Main Interface](path/to/main_interface_image.png) -->
## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Launching the GUI](#launching-the-gui)
  - [Configuring Experiments](#configuring-experiments)
  - [Running Experiments](#running-experiments)
- [Data Management](#data-management)
- [Experiment Types](#experiment-types)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

Experiment Configuration GUI: Easily configure participant information and experiment blocks without editing code.
Multi-Block Support: Run a series of experiments with different configurations in a single session.
Data Integration with REDCap: Automatically upload collected data to REDCap for centralized management.
Audiovisual Synchrony Correction: Adjust for hardware-induced discrepancies between audio and visual stimuli.
Support for Various Experiment Types: Including Simultaneity Judgment (SJ), Simple Reaction Time (SRT), and their modified versions.

## Prerequisites

- Anaconda or Miniconda (for conda environment management)
- Python 3.6 or higher
- PsychoPy: For running the experiments.
- PyQt5: For the GUI application.
- Redcap: Python module for interacting with REDCap API.
- Additional Libraries:
  - numpy
  - json
  - csv
  - platform
  - random
  - os
  - sys
  - datetime
  - subprocess

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/Python-MSI-Suite.git
   cd Python-MSI-Suite
   ```

2. **Create and Activate a Conda Environment Using the Provided YAML File**

   ```bash
   conda env create -f environment.yaml
   conda activate python-suite
   ```

   This command creates a new conda environment named `python-suite` with all the required packages specified in `environment.yaml`.

3. **(Optional) Install Additional Packages**

   If you need to install additional packages or face issues with the provided environment, you can install required packages manually.

   ```bash
   pip install -r requirements.txt
   ```

   *(Note: Ensure that you are in the `python-suite` environment when running this command.)*

Configure REDCap API Credentials *(Optional)*

If you wish to integrate with REDCap, create a file named `api_text.txt` in the root directory.

Add the following lines with your REDCap API URL and token:

```text
api_url=https://your_redcap_url/api/
api_token=your_api_token_here
```

**Note:** If you do not provide REDCap API credentials, you can still run the program offline. The data will be saved locally without being uploaded to REDCap.

<!-- ![API Credentials Setup](path/to/api_credentials_image.png) -->
## Usage
### Launching the Experiment Configuration GUI
Run the following command in your terminal:

<!-- ![Experiment Configuration GUI](path/to/experiment_gui_image.png) -->
### Configuring Experiments
#### Participant Information
Participant ID: Select or enter a participant ID. Existing IDs from REDCap will be loaded automatically.
Age: Enter the participant's age.
Gender: Select the participant's gender.
Site: Choose the site where the experiment is conducted.
Fullscreen Mode: Check this option to run experiments in fullscreen.
<!-- ![Participant Information](path/to/participant_info_image.png) -->
#### Audiovisual Synchrony Correction
Adjust the synchronization between audio and visual stimuli by entering a correction value in milliseconds.

<!-- ![AV Synchrony Correction](path/to/av_sync_image.png) -->
#### Blocks Configuration
Click on "Add Block" to introduce a new experimental block.
For each block:
Experiment Type: Choose from SJ, SRT, SRT_Mod, SJ_Mod.
Trials per Condition: Set the number of trials for each condition.
Additional Options: Depending on the experiment type, additional configuration options may appear (e.g., left audio high pitch).
<!-- ![Blocks Configuration](path/to/blocks_config_image.png) -->
#### Estimated Experiment Time
The application automatically calculates and displays the total estimated time for the experiment based on your configurations.

<!-- ![Estimated Time](path/to/estimated_time_image.png) -->
#### Saving and Loading Configurations
Save Configuration: Click on "Save Configuration" to save your current setup to a JSON file.
Load Configuration: Use "Load Configuration" to load a previously saved setup.
The application also saves your REDCap API credentials when you save a configuration.
### Running Experiments
After configuring your experiment:

Click on "Save and Run Experiment".
The application will prompt you that it will start in a separate process and the GUI will close.
The experiment will begin running, displaying stimuli according to your configuration.
<!-- ![Running Experiment](path/to/running_experiment_image.png) -->
Note: Ensure your system volume is appropriate, and the participant is ready before starting.

## Data Management
### Local Data Saving
Data collected during the experiments are saved locally in CSV format.
Filenames include participant ID, age, gender, site, and a timestamp for easy identification.
Example filename: data_001_25_m_vandy_20231115_123456.csv
### Uploading Data to REDCap *(Optional)*
If REDCap API credentials are provided, collected data are automatically uploaded to REDCap using the provided API credentials.
Demographic data and experimental results are stored as separate records for better organization.
**If no REDCap API URL or API token is provided, the program will run offline and save the data locally without attempting to upload to REDCap.**
## Experiment Types
### SJ (Simultaneity Judgment)
Participants judge whether audio and visual stimuli occur simultaneously.

Stimuli: Red circle (visual), tone (audio).
Response: Press '1' for same time, '2' for different times.
<!-- ![SJ Trial](path/to/sj_trial_image.png) -->
### SRT (Simple Reaction Time)
Participants respond as quickly as possible when they detect a stimulus.

Stimuli: Either visual, auditory, or both.
Response: Press the spacebar upon detection.
<!-- ![SRT Trial](path/to/srt_trial_image.png) -->
### SRT_Mod (Modified Simple Reaction Time)
An extension of SRT with lateralized stimuli and varied pitches/colors.

Stimuli: Left/right/bilateral presentations with low/high pitches and green/red circles.
Customization: Options to set left/right attributes.
<!-- ![SRT_Mod Trial](path/to/srt_mod_trial_image.png) -->
### SJ_Mod (Modified Simultaneity Judgment)
Combines elements of SJ and SRT_Mod for more complex judgment tasks.

Stimuli: Various SOAs (Stimulus Onset Asynchronies), lateralized stimuli.
Response: Similar to SJ but includes side distinctions.
<!-- ![SJ_Mod Trial](path/to/sj_mod_trial_image.png) -->
## Customization
Experiment parameters such as stimulus duration, colors, and positions can be customized in the code if needed.
Audio files (tone.wav, low_pitch.wav, high_pitch.wav) can be replaced with alternatives, but ensure filenames match those in the code.
## Troubleshooting
Application Won't Start: Ensure all prerequisites are installed and you're running the correct Python version.
Audio Issues: Check your system's audio settings and that the correct audio library (PTB) is available.
REDCap Connection Errors: Verify your API URL and token. Ensure you have network connectivity.
