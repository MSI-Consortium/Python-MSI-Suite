#!/usr/bin/env python3
from psychopy import prefs  # Configure preferences first
# prefs.hardware['audioLib'] = ['sounddevice', 'pyo']
prefs.hardware['audioDriver'] = ['Primary Sound', 'ASIO', 'Windows DirectSound', 'Windows WDM-KS']
prefs.hardware['audioLib'] = ['PTB']  # Set PTB as preferred audio engine
from psychopy import sound, core

print("Audio preferences set.")
sound.init()  # Initialize sound system now that prefs are set
print(f"Audio Library Used: {sound.audioLib}")
print(f"Available Audio Devices: {sound.getDevices()}")

print("Playing a 440Hz tone for 1 second...")
# Create a simple 440Hz tone
test_sound = sound.Sound(400, secs=1.0)
test_sound.setVolume(1.0)
test_sound.play()
core.wait(1.5)
print("Sound test complete.")
core.quit()
