import os
import numpy as np
from scipy.io.wavfile import write
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox

def create_tone(filename, frequency, duration=0.1, fs=44100):
    """Create a tone and save it as a WAV file."""
    samples = np.arange(duration * fs) / fs
    waveform = np.sin(2 * np.pi * frequency * samples)
    waveform_integers = np.int16(waveform * 32767)
    write(filename, fs, waveform_integers)
    print(f"Created {filename}")

def main():
    app = QApplication([])
    window = QWidget()
    window.setWindowTitle("Sound Creator")
    label = QLabel("Sound files are missing.\nClick the button below to create them.")
    create_button = QPushButton("Create Sound Files")

    def on_create():
        directory = os.path.dirname(__file__)
        create_tone(os.path.join(directory, "tone.wav"), frequency=1000)
        create_tone(os.path.join(directory, "high_pitch.wav"), frequency=1500)
        create_tone(os.path.join(directory, "low_pitch.wav"), frequency=500)
        QMessageBox.information(window, "Success", "Sound files created successfully.")
        window.close()

    create_button.clicked.connect(on_create)

    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(create_button)
    window.setLayout(layout)
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()