#!/usr/bin/env python3
from psychopy import prefs  # Configure preferences first
# prefs.hardware['audioLib'] = ['sounddevice', 'pyo']
prefs.hardware['audioDriver'] = ['Primary Sound', 'ASIO', 'Windows DirectSound', 'Windows WDM-KS']
prefs.hardware['audioLib'] = ['PTB']  # Set PTB as preferred audio engine
from psychopy import sound, core

print("Audio preferences set.")

# Initialize sound system (not available in all PsychoPy versions)
try:
    sound.init()
except AttributeError:
    pass  # Sound system initializes automatically when creating Sound objects

# Handle different PsychoPy versions for audioLib attribute
try:
    audio_lib = sound.audioLib
except AttributeError:
    audio_lib = prefs.hardware['audioLib']
print(f"Audio Library Used: {audio_lib}")

# Get available devices (not available in all PsychoPy versions)
try:
    print(f"Available Audio Devices: {sound.getDevices()}")
except AttributeError:
    print("Audio device listing not available in this PsychoPy version")

print("Playing a 440Hz tone for 1 second...")
# Create a simple 440Hz tone
test_sound = sound.Sound(400, secs=1.0)
test_sound.setVolume(1.0)
test_sound.play()
core.wait(1.5)
print("Sound test complete.")
core.quit()
