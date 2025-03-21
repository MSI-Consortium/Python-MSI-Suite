#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 07:48:19 2024

@author: David Tovar
"""
import platform
import random
import os
import csv
import json
import sys
from datetime import datetime
from psychopy import visual, core, event, monitors, sound
from psychopy import prefs

# Configure audio settings before importing sound - using only PTB for reliability
prefs.hardware['audioLib'] = ['PTB']  # Using only PTB (PsychToolbox) as it's most reliable
prefs.general['audioDevice'] = 'default'  # Use system default audio device

print("\nAudio Configuration:")
print(f"Selected Audio Library: {sound.audioLib}")
print(f"Audio Device: {prefs.general['audioDevice']}")
sound.init()  # Explicitly initialize sound system

import numpy as np
import redcap
import subprocess  # Add this import at the top

def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def check_and_upload_offline_files(api_url, api_token):
    """Check for offline data files and upload them to REDCap if online.
    
    Fetches the latest record ID from REDCap and ensures offline files
    are correctly numbered before upload.
    """
    try:
        print("\nChecking for offline data files...")
        offline_files = []
        
        # Find all data files with 'offline' in the filename
        for file in os.listdir():
            if file.startswith('data_') and file.endswith('.csv') and 'offline' in file:
                offline_files.append(file)
                
        # Also find offline demographic files
        for file in os.listdir():
            if file.startswith('demographic_data_') and file.endswith('.csv') and 'offline' in file:
                offline_files.append(file)
        
        if not offline_files:
            print("No offline files found.")
            return
            
        print(f"Found {len(offline_files)} offline files.")
        
        # Try to connect to REDCap and get the latest record ID
        try:
            project = redcap.Project(api_url, api_token)
            print("Connected to REDCap project for offline file upload.")
            
            # Get all existing record IDs to find the highest one
            try:
                records = project.export_records(fields=['record_id'])
                record_ids = [int(record['record_id']) for record in records if record['record_id'].isdigit()]
                
                if record_ids:
                    next_id = max(record_ids) + 1
                else:
                    next_id = 1
                    
                print(f"Next available REDCap record ID: {next_id}")
                
                # Group files by participant to ensure data and demographic files for the same 
                # participant get the same new ID
                participant_files = {}
                
                for file in offline_files:
                    parts = file.split('_')
                    if file.startswith('data_'):
                        participant_id = parts[1]
                    else:  # demographic file
                        participant_id = parts[2]
                    
                    if participant_id not in participant_files:
                        participant_files[participant_id] = []
                    
                    participant_files[participant_id].append(file)
                
                # Process files in batches by participant, assigning new sequential IDs
                for offline_id, files in participant_files.items():
                    new_id_str = str(next_id).zfill(3)  # Format with leading zeros
                    print(f"Assigning ID {new_id_str} to offline participant {offline_id}")
                    
                    for file in files:
                        # Prepare the record and upload
                        record_data = [{'record_id': new_id_str}]
                        project.import_records(record_data)
                        
                        # Create new filename before upload
                        if file.startswith('data_'):
                            # Format: data_ID_age_gender_site_offline_timestamp.csv
                            parts = file.split('_')
                            timestamp = parts[-1]  # Get timestamp
                            age = parts[2]
                            gender = parts[3]
                            site = parts[4]
                            new_filename = f"data_{new_id_str}_{age}_{gender}_{site}_{timestamp}"
                        else:
                            # Format: demographic_data_ID_offline_timestamp.csv
                            parts = file.split('_')
                            timestamp = parts[-1]  # Get timestamp
                            new_filename = f"demographic_data_{new_id_str}_{timestamp}"
                        
                        print(f"Renaming {file} to {new_filename} for upload")
                        
                        # Determine the field name for upload
                        if file.startswith('data_'):
                            field_name = 'python_data_file'
                        else:
                            field_name = 'demographic_data_file'
                        
                        # Upload file with the new ID
                        try:
                            with open(file, 'rb') as f:
                                file_content = f.read()
                                
                                # For data files, we need to update the participant ID inside the CSV content
                                if file.startswith('data_'):
                                    # Read the file, update the participant ID in the content
                                    with open(file, 'r') as csv_file:
                                        lines = csv_file.readlines()
                                        
                                    header = lines[0]
                                    updated_lines = [header]
                                    
                                    # Update each data row with the new participant ID
                                    for line in lines[1:]:
                                        data = line.split(',')
                                        data[0] = new_id_str  # Replace participant ID
                                        updated_lines.append(','.join(data))
                                    
                                    # Write updated content to the new file
                                    with open(new_filename, 'w') as new_file:
                                        new_file.writelines(updated_lines)
                                        
                                    # Now read the updated file for upload
                                    with open(new_filename, 'rb') as new_file:
                                        file_content = new_file.read()
                                else:
                                    # Simply rename the demographic file and update its content
                                    with open(file, 'r') as csv_file:
                                        lines = csv_file.readlines()
                                        
                                    header = lines[0]
                                    # There should be only one data row in demographic files
                                    if len(lines) > 1:
                                        data = lines[1].split(',')
                                        data[0] = new_id_str  # Replace participant ID
                                        updated_content = header + ','.join(data)
                                        
                                        with open(new_filename, 'w') as new_file:
                                            new_file.write(updated_content)
                                            
                                        with open(new_filename, 'rb') as new_file:
                                            file_content = new_file.read()
                            
                            # Upload the file with the new name and ID
                            project.import_file(
                                record=new_id_str,
                                field=field_name,
                                file_name=new_filename,
                                file_content=file_content
                            )
                            
                            print(f"Successfully uploaded {new_filename} to REDCap with ID {new_id_str}")
                            
                            # Delete the original offline file since we've created a renamed version
                            if os.path.exists(file):
                                os.remove(file)
                                print(f"Removed original offline file: {file}")
                                
                        except Exception as e:
                            print(f"Error processing {file}: {str(e)}")
                            continue
                    
                    # Increment the ID for the next participant
                    next_id += 1
                    
            except Exception as e:
                print(f"Error fetching REDCap records: {str(e)}")
                return
                    
        except Exception as e:
            print(f"Error connecting to REDCap: {str(e)}")
            return
            
    except Exception as e:
        print(f"Error checking for offline files: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return

def load_api_credentials(filename="api_text.txt"):
    """Load API URL and token from file. Returns None if not found or incomplete."""
    api_url = None
    api_token = None

    if os.path.exists(filename):
        with open(filename, 'r') as file:
            for line in file:
                key_value = line.strip().split('=')
                if len(key_value) == 2:
                    key, value = key_value
                    if key == 'api_url':
                        api_url = value
                    elif key == 'api_token':
                        api_token = value

    if not api_url or not api_token:
        print("API credentials not found or incomplete. REDCap upload will be skipped.")
        return None, None

    return api_url, api_token

# Load API credentials
api_url, api_token = load_api_credentials()

# Initialize REDCap project if credentials are available and not in offline mode
config = load_config(sys.argv[1])
offline_mode = config.get('offline_mode', False)

if api_url and api_token and not offline_mode:
    try:
        project = redcap.Project(api_url, api_token)
        print("\nVerifying REDCap connection...")
        project_info = project.export_project_info()
        print(f"Connected to REDCap project: {project_info['project_title']}")
        
        # Check for offline files and upload them
        check_and_upload_offline_files(api_url, api_token)
    except Exception as e:
        print(f"Error connecting to REDCap: {e}")
        project = None
else:
    if offline_mode:
        print("Running in offline mode. Data will be saved locally.")
    else:
        print("REDCap credentials not available. Running in offline mode.")
    project = None

# Detect operating system
RUNNING_ON_MAC = platform.system() == 'Darwin'
print(f"Running on {'Mac' if RUNNING_ON_MAC else 'Windows/Linux'}")

# OS-specific settings
if RUNNING_ON_MAC:
    WINDOW_CONFIG = {
        'fullscr': False,
        'waitBlanking': True,
        'allowGUI': True,
        'screen': 0,
        'backendConf': {'gl_version': '2,1'},
        'useRetina': True
    }
else:
    WINDOW_CONFIG = {
        'fullscr': False,
        'waitBlanking': True,
        'allowGUI': True,
        'screen': 0
    }




def save_demographic_data(config):
    """Save demographic data to CSV and create REDCap record if possible."""
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # Add offline tag to filename if in offline mode
    offline_mode = config.get('offline_mode', False)
    offline_tag = "_offline" if offline_mode else ""
    demo_filename = f"demographic_data_{config['participant_id']}{offline_tag}_{timestamp}.csv"
    
    # Save demographic data to CSV
    with open(demo_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['record_id', 'age', 'gender'])
        writer.writerow([config['participant_id'], config['age'], config['gender']])
    
    # Skip REDCap upload if in offline mode
    if offline_mode:
        print("Running in offline mode. Demographic data saved locally.")
        return demo_filename
    
    if project:
        try:
            # First create/update just the record_id
            data = {
                'record_id': config['participant_id']
            }
            
            # Import just the record_id
            response = project.import_records([data])
            print(f"Created/Updated record for participant: {config['participant_id']}")
            
            # Now upload the CSV file as an attachment
            try:
                with open(demo_filename, 'rb') as file:
                    file_content = file.read()
                    response = project.import_file(
                        record=config['participant_id'],
                        field='demographic_data_file',
                        file_name=demo_filename,
                        file_content=file_content
                    )
                print(f"Uploaded demographic CSV file for participant: {config['participant_id']}")
            except Exception as e:
                print(f"Error uploading demographic file: {e}")
                # Continue execution even if file upload fails
        except Exception as e:
            print(f"Error creating REDCap record: {e}")
            # Continue execution even if REDCap upload fails
    else:
        print("REDCap project not initialized. Skipping REDCap upload.")

    return demo_filename

# Replace existing config loading code with:
if len(sys.argv) < 2:
    print("Please provide a configuration file.")
    sys.exit(1)

config = load_config(sys.argv[1])
demographic_file = save_demographic_data(config)
print(f"Demographic data saved to: {demographic_file}")


# Common parameters
bg_color = [255, 255, 255]  # White
win_width = 1300
win_height = 800
distance = 57  # cm
stim_size = 2  # degrees
VISUAL_STIM_DURATION = 0.1

# Set up the window with timing-critical settings
mon = monitors.Monitor('testMonitor')
mon.setWidth(32)
mon.setDistance(distance)
mon.setSizePix((win_width, win_height))

# Create window with Mac-specific settings
win = visual.Window([win_width, win_height], 
                   color=[c/255 for c in bg_color], 
                   units="deg", 
                   monitor=mon,
                   **WINDOW_CONFIG)
# Get frame rate once at startup
try:
    actual_fps = win.getActualFrameRate(nIdentical=10, nMaxFrames=100, nWarmUpFrames=10)
    if actual_fps is None:
        actual_fps = 60.0  # Common Mac refresh rate
    frame_dur = 1.0/actual_fps
except:
    actual_fps = 60.0
    frame_dur = 1.0/60.0

print(f"Using refresh rate: {actual_fps}Hz")
VISUAL_FRAMES = max(1, int(VISUAL_STIM_DURATION * actual_fps))
print(f"Frames per stimulus: {VISUAL_FRAMES}")

# Create common stimuli
fixation = visual.ShapeStim(win, 
    vertices=((0, -0.5), (0, 0.5), (0,0), (-0.5,0), (0.5, 0)),
    lineWidth=5,
    closeShape=False,
    lineColor="black"
)

# Move to top, after imports
def verify_visual_timing(win, target_dur):
    """Returns True if the last visual timing was acceptable"""
    return abs(win.lastFrameT - target_dur) < 0.001  # 1ms tolerance

def create_sound(filename, duration):
    """Create and configure a sound stimulus with improved error handling"""
    try:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        print(f"\nAttempting to create sound: {filepath}")
        print(f"Using audio library: {sound.audioLib}")
        
        # Create sound with PTB backend
        try:
            sound_stim = sound.Sound(filepath, secs=duration)
            sound_stim.setVolume(0.8)  # Set to 80% volume for safety
            
            # Test the sound
            print("Testing sound playback...")
            sound_stim.play()
            core.wait(0.1)  # Wait briefly
            sound_stim.stop()
            print("Sound test complete")
            
            return sound_stim
        except Exception as e:
            print(f"Error creating sound: {e}")
            print("Sound system details:")
            print(f"Audio library: {sound.audioLib}")
            if os.path.exists(filepath):
                print(f"Sound file exists at {filepath}")
            else:
                print(f"Sound file not found at {filepath}")
                print("Attempting to create sound files using sound_creator.py")
                subprocess.call(["python", "sound_creator.py"])
                if os.path.exists(filepath):
                    try:
                        sound_stim = sound.Sound(filepath, secs=duration)
                        sound_stim.setVolume(0.8)
                        return sound_stim
                    except Exception as new_e:
                        print(f"Failed to create sound even after regenerating file: {new_e}")
        
        # If we get here, nothing worked
        print("Unable to initialize sound system. Please check your audio settings and device.")
        return None
        
    except Exception as e:
        print(f"Error in create_sound: {e}")
        return None

def cleanup():
    """Clean up resources properly"""
    try:
        # Stop any playing sounds by stopping individual sound objects
        # If you have multiple sound objects, stop them individually
        # Example:
        # sound_stim.stop()
        win.close()
    finally:
        core.quit()

def show_instructions(text):
    instructions = visual.TextStim(win, text=text, color="black", height=0.7, wrapWidth=30)
    while True:
        instructions.draw()
        win.flip()
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'space' in keys:
            return
        if 'escape' in keys:
            win.close()
            core.quit()
        core.wait(0.001)

def run_sj_trial(soa, visual_stim, sound_stim, instructions, trial_counter):
    print(f"\nStarting SJ trial with SOA: {soa}ms")
    av_sync = config.get('av_sync_correction', 0.0)
    adjusted_soa = soa + av_sync
    print(f"AV sync correction: {av_sync}ms, Adjusted SOA: {adjusted_soa}ms")
    
    # Create SOA display text for test mode
    test_mode = config.get('test_mode', False)
    soa_text = None
    if test_mode:
        if soa < 0:
            soa_display = f"A{abs(soa)}V"
        elif soa > 0:
            soa_display = f"V{soa}A"
        else:
            soa_display = "SYNC"
        soa_text = visual.TextStim(win, text=f"{soa_display} (corr: {av_sync}ms)", 
                                 color="black", height=0.5, pos=(0, 3))
    
    response_made = False
    rt = None
    response = -1
    
    # Additional elements to draw with the visual stimulus
    additional_stims = [instructions, trial_counter]
    if test_mode and soa_text:
        additional_stims.append(soa_text)
    
    # Pre-trial setup
    fixation.draw()
    for stim in additional_stims:
        stim.draw()
    win.flip()
    core.wait(random.uniform(1, 2))  # Random foreperiod
    
    trial_clock = core.Clock()
    
    # Ensure visual stimulus duration is constant
    visual_duration = VISUAL_FRAMES * frame_dur
    
    if adjusted_soa <= 0:  # Audio first or simultaneous
        if adjusted_soa == 0:  # Truly simultaneous
            # For simultaneous presentation, play audio in a separate step
            # to avoid timing issues that can shorten the visual stimulus
            
            # First, reset the clock but don't play audio yet
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Now draw visual and play audio
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(sound_stim.play)
            win.flip()
            
            # Use robust presentation for remaining frames
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
        
        else:  # Audio leads
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(sound_stim.play)
            win.flip()
            
            # Wait for SOA
            frames_to_wait = round(abs(adjusted_soa/1000.0) / frame_dur)
            for frame in range(frames_to_wait):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip()
            
            # Use robust presentation for visual stimulus
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES, additional_stims)
    
    else:  # Visual first
        # Show visual for its full duration
        fixation.draw()
        visual_stim.draw()
        for stim in additional_stims:
            stim.draw()
        win.callOnFlip(trial_clock.reset)
        win.flip()
        
        # Use robust presentation for remaining frames
        ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
        
        # Wait until time to play audio
        frames_to_wait = round((adjusted_soa/1000.0 - visual_duration) / frame_dur)
        frames_to_wait = max(0, frames_to_wait)
        
        for frame in range(frames_to_wait):
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.flip()
        
        # Play audio
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.callOnFlip(sound_stim.play)
        win.flip()
    
    # Modified response collection - wait indefinitely until response
    while not response_made:
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.flip()
        
        keys = event.getKeys(timeStamped=trial_clock, keyList=['1', '2', 'escape'])
        if keys:
            if 'escape' in keys[0][0]:
                cleanup()
            else:
                rt = keys[0][1]
                response = 1 if keys[0][0] == '1' else 2
                response_made = True
                print(f"Response: {response} at {rt}s")
    
    sound_stim.stop()
    return response, rt

def run_srt_trial(trial_type, visual_stim, sound_stim, instructions, feedback):
    print(f"\nStarting SRT trial: {trial_type}")
    av_sync = config.get('av_sync_correction', 0.0)
    print(f"AV sync correction: {av_sync}ms")
    response_made = False
    rt = None
    
    # Create correction text for test mode
    test_mode = config.get('test_mode', False)
    correction_text = None
    if test_mode:
        correction_text = visual.TextStim(win, text=f"(corr: {av_sync}ms)", 
                                         color="black", height=0.5, pos=(0, 3))
    
    # Additional elements to draw with the visual stimulus
    additional_stims = [feedback]
    if test_mode and correction_text:
        additional_stims.append(correction_text)
    
    # Pre-trial setup
    fixation.draw()
    for stim in additional_stims:
        stim.draw()
    win.flip()
    foreperiod = random.uniform(1, 3)
    print(f"Waiting foreperiod: {foreperiod}s")
    core.wait(foreperiod)
    
    trial_clock = core.Clock()
    trial_clock.reset()
    stim_onset = None
    
    # Present stimulus
    if trial_type == 'audiovisual':
        print(f"Starting AV stimulus with {av_sync}ms offset")
        if av_sync <= 0:  # Audio first or simultaneous
            if av_sync == 0:  # Truly simultaneous
                # First, reset the clock but don't play audio yet
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(trial_clock.reset)
                win.flip()
                
                # Now draw visual and play audio together
                fixation.draw()
                visual_stim.draw()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(sound_stim.play)
                win.flip()
                stim_onset = trial_clock.getTime()
                
                # Use our robust presentation method for remaining frames
                ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
            
            else:  # Audio leads
                print("Playing audio")
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(trial_clock.reset)
                win.callOnFlip(sound_stim.play)
                win.flip()
                
                # Wait for SOA
                wait_frames = round(abs(av_sync/1000.0) / frame_dur)
                for frame in range(wait_frames):
                    fixation.draw()
                    for stim in additional_stims:
                        stim.draw()
                    win.flip()
                
                # Show visual for full duration using our robust method
                stim_onset = trial_clock.getTime()
                ensure_visual_presentation(visual_stim, VISUAL_FRAMES, additional_stims)
                
        else:  # Visual first
            # Start with visual
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            stim_onset = trial_clock.getTime()
            
            # Use robust presentation for remaining visual frames
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
            
            # Calculate frames to wait before audio
            frames_to_wait = round((av_sync/1000.0) / frame_dur)
            
            win.callOnFlip(trial_clock.reset)
            win.flip()
            stim_onset = trial_clock.getTime()
            
            # Ensure full VISUAL_FRAMES duration
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                visual_stim.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip()
            
            # Calculate frames to wait before audio
            frames_to_wait = round((av_sync/1000.0) / frame_dur)
            
            # Wait until audio should start
            for frame in range(frames_to_wait):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip()
            
            # Play audio
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(sound_stim.play)
            win.flip()
            
    elif trial_type == 'visual':
        # Visual only trial
        fixation.draw()
        visual_stim.draw()
        for stim in additional_stims:
            stim.draw()
        win.callOnFlip(trial_clock.reset)
        win.flip()
        stim_onset = trial_clock.getTime()
        
        # Ensure full VISUAL_FRAMES duration
        for frame in range(VISUAL_FRAMES - 1):
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.flip()
            
    else:  # audio
        print("Starting audio stimulus")
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.callOnFlip(trial_clock.reset)
        win.callOnFlip(sound_stim.play)
        win.flip()
        stim_onset = trial_clock.getTime()
        
        # Show fixation for consistent duration (matching visual)
        for frame in range(VISUAL_FRAMES - 1):
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.flip()
    
    # Response collection
    response_window = 2.0  # Allow 2 seconds for response
    while (trial_clock.getTime() - stim_onset) < response_window and not response_made:
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.flip()
        
        keys = event.getKeys(['space', 'escape'], timeStamped=trial_clock)
        for key in keys:
            if key[0] == 'escape':
                cleanup()
            elif key[0] == 'space':
                rt = key[1] - stim_onset
                response_made = True
                print(f"Response at {rt}s")
                break
    
    sound_stim.stop()
    
    if rt is not None and rt < 0.05:
        print("Response too fast")
        return None
    
    return rt

def run_srt_mod_trial(trial_type, visual_stim_left, visual_stim_right, sound_left, sound_right, instructions, feedback):
    print(f"\nStarting SRT_Mod trial: {trial_type}")
    av_sync = config.get('av_sync_correction', 0.0)
    print(f"AV sync correction: {av_sync}ms")
    response_made = False
    rt = None
    
    # Create correction text for test mode
    test_mode = config.get('test_mode', False)
    correction_text = None
    if test_mode:
        correction_text = visual.TextStim(win, text=f"(corr: {av_sync}ms)", 
                                         color="black", height=0.5, pos=(0, 3))
    
    # Additional elements to draw with the visual stimulus
    additional_stims = [feedback, instructions]
    if test_mode and correction_text:
        additional_stims.append(correction_text)
    
    # Pre-trial setup
    fixation.draw()
    for stim in additional_stims:
        stim.draw()
    win.flip()
    core.wait(random.uniform(1, 3))
    
    trial_clock = core.Clock()
    trial_clock.reset()
    stim_onset = 0  # We'll reset the clock at stimulus onset
    
    # Helper functions remain unchanged
    def get_visual_stim():
        if '_left' in trial_type:
            return visual_stim_left
        elif '_right' in trial_type:
            return visual_stim_right
        elif '_bilateral' in trial_type:
            return None
        return None

    def draw_bilateral():
        visual_stim_left.draw()
        visual_stim_right.draw()
        
    # Present stimulus
    if 'audiovisual' in trial_type:
        # Stop any playing sounds
        sound_left.stop()
        sound_right.stop()
        
        if av_sync <= 0:  # Audio first or simultaneous
            if av_sync == 0:  # Truly simultaneous
                # For bilateral stimuli
                if '_bilateral' in trial_type:
                    # Reset the clock first
                    fixation.draw()
                    for stim in additional_stims:
                        stim.draw()
                    win.callOnFlip(trial_clock.reset)
                    win.flip()
                    
                    # Now start visual and audio together
                    fixation.draw()
                    draw_bilateral()
                    for stim in additional_stims:
                        stim.draw()
                    
                    # Schedule audio
                    if '_left' in trial_type:
                        win.callOnFlip(sound_left.play)
                    elif '_right' in trial_type:
                        win.callOnFlip(sound_right.play)
                    else:  # bilateral
                        win.callOnFlip(sound_left.play)
                        win.callOnFlip(sound_right.play)
                    
                    win.flip()
                    
                    # Use our new robust method to ensure visual presentation
                    # Create a temporary custom function for bilateral presentation
                    def draw_bilateral_with_fixation():
                        fixation.draw()
                        draw_bilateral()
                        for stim in additional_stims:
                            stim.draw()
                        
                    # We handle this special case with a loop because ensure_visual_presentation 
                    # expects a single visual stim object
                    for frame in range(VISUAL_FRAMES - 1):
                        fixation.draw()
                        draw_bilateral()
                        for stim in additional_stims:
                            stim.draw()
                        win.flip()
                else:
                    # Single stimulus case - use our robust methods
                    visual_stim = get_visual_stim()
                    
                    # Reset the clock first
                    fixation.draw()
                    for stim in additional_stims:
                        stim.draw()
                    win.callOnFlip(trial_clock.reset)
                    win.flip()
                    
                    # Now start visual and audio together
                    fixation.draw()
                    visual_stim.draw()
                    for stim in additional_stims:
                        stim.draw()
                    
                    # Schedule audio
                    if '_left' in trial_type:
                        win.callOnFlip(sound_left.play)
                    elif '_right' in trial_type:
                        win.callOnFlip(sound_right.play)
                    
                    win.flip()
                    
                    # Use robust presentation for remaining frames
                    ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
                        
            else:  # Audio leads
                # Play audio first
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(trial_clock.reset)
                
                if '_left' in trial_type:
                    win.callOnFlip(sound_left.play)
                elif '_right' in trial_type:
                    win.callOnFlip(sound_right.play)
                else:  # bilateral
                    win.callOnFlip(sound_left.play)
                    win.callOnFlip(sound_right.play)
                
                win.flip()
                
                # Wait for SOA
                frames_to_wait = round(abs(av_sync/1000.0) / frame_dur)
                for frame in range(frames_to_wait):
                    fixation.draw()
                    for stim in additional_stims:
                        stim.draw()
                    win.flip()
                
                # Show visual for full duration
                if '_bilateral' in trial_type:
                    # Bilateral case - use manual drawing with a guaranteed frame rate
                    for frame in range(VISUAL_FRAMES):
                        fixation.draw()
                        draw_bilateral()
                        for stim in additional_stims:
                            stim.draw()
                        win.flip(clearBuffer=True)
                else:
                    # Single visual stimulus - use our robust method
                    visual_stim = get_visual_stim()
                    ensure_visual_presentation(visual_stim, VISUAL_FRAMES, additional_stims)
                    
        else:  # Visual first
            # Start with visual
            if '_bilateral' in trial_type:
                fixation.draw()
                draw_bilateral()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(trial_clock.reset)
                win.flip()
                
                # Bilateral case - use manual drawing with a guaranteed frame rate
                for frame in range(VISUAL_FRAMES - 1):
                    fixation.draw()
                    draw_bilateral()
                    for stim in additional_stims:
                        stim.draw()
                    win.flip(clearBuffer=True)
            else:
                visual_stim = get_visual_stim()
                fixation.draw()
                visual_stim.draw()
                for stim in additional_stims:
                    stim.draw()
                win.callOnFlip(trial_clock.reset)
                win.flip()
                
                # Use robust presentation for remaining frames
                ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
            
            # Calculate time to wait before audio
            frames_to_wait = round((av_sync/1000.0) / frame_dur)
            
            # Wait until audio should start
            for frame in range(frames_to_wait):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip()
            
            # Play audio
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            
            if '_left' in trial_type:
                win.callOnFlip(sound_left.play)
            elif '_right' in trial_type:
                win.callOnFlip(sound_right.play)
            else:  # bilateral
                win.callOnFlip(sound_left.play)
                win.callOnFlip(sound_right.play)
            
            win.flip()
    
    elif 'visual' in trial_type:
        # Visual only trial
        if '_bilateral' in trial_type:
            fixation.draw()
            draw_bilateral()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Bilateral case - use manual drawing with a guaranteed frame rate
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                draw_bilateral()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
        else:
            visual_stim = get_visual_stim()
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Use robust presentation for remaining frames
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
    
    elif 'audio' in trial_type:
        # Audio only trial
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.callOnFlip(trial_clock.reset)
        
        if '_left' in trial_type:
            win.callOnFlip(sound_left.play)
        elif '_right' in trial_type:
            win.callOnFlip(sound_right.play)
        else:  # bilateral
            win.callOnFlip(sound_left.play)
            win.callOnFlip(sound_right.play)
        
        win.flip()
        
        # Show fixation for consistent duration
        for frame in range(VISUAL_FRAMES - 1):
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.flip()
    
    # Response collection
    response_window = 2.0  # Allow 2 seconds for response
    while (trial_clock.getTime()) < response_window and not response_made:
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.flip()
        
        keys = event.getKeys(['space', 'escape'], timeStamped=trial_clock)
        for key in keys:
            if key[0] == 'escape':
                cleanup()
            elif key[0] == 'space':
                rt = key[1]  # Already relative to stim_onset since we reset clock at stimulus
                response_made = True
                print(f"Response at {rt}s")
                break
    
    # End trial - stop all sounds
    sound_left.stop()
    sound_right.stop()
    
    if rt is not None and rt < 0.05:
        print("Response too fast")
        return None
    
    return rt

def run_sj_mod_trial(trial_type, soa, side, visual_stim_left, visual_stim_right, sound_left, sound_right, instructions, trial_counter):
    print(f"\nStarting SJ_Mod trial: {trial_type}, SOA: {soa}ms, Side: {side}")
    av_sync = config.get('av_sync_correction', 0.0)
    adjusted_soa = soa + av_sync
    print(f"AV sync correction: {av_sync}ms, Adjusted SOA: {adjusted_soa}ms")
    
    # Create SOA display text for test mode
    test_mode = config.get('test_mode', False)
    soa_text = None
    if test_mode:
        # Format test mode display text depending on trial type
        if trial_type == 'audiovisual':
            side_marker = "L" if side == "left" else "R"
            if soa < 0:  # Audio first
                soa_display = f"A{side_marker}{abs(soa)}V{side_marker}"
            elif soa > 0:  # Visual first
                soa_display = f"V{side_marker}{soa}A{side_marker}"
            else:  # Simultaneous
                soa_display = f"AV-SYNC-{side_marker}"
        elif trial_type == 'visual':
            first_marker = "L" if side == "left" else "R"
            second_marker = "R" if side == "left" else "L"
            if soa == 0:
                soa_display = "V-SYNC"
            else:
                soa_display = f"V{first_marker}{abs(soa)}V{second_marker}"
        else:  # auditory
            first_marker = "L" if side == "left" else "R"
            second_marker = "R" if side == "left" else "L"
            if soa == 0:
                soa_display = "A-SYNC"
            else:
                soa_display = f"A{first_marker}{abs(soa)}A{second_marker}"
        
        soa_text = visual.TextStim(win, text=f"{trial_type}: {soa_display} (corr: {av_sync}ms)", 
                                  color="black", height=0.5, pos=(0, 3))
    
    response_made = False
    rt = None
    response = -1
    
    # Additional elements to draw
    additional_stims = [instructions, trial_counter]
    if test_mode and soa_text:
        additional_stims.append(soa_text)
    
    # Pre-trial setup
    fixation.draw()
    for stim in additional_stims:
        stim.draw()
    win.flip()
    core.wait(random.uniform(1, 2))
    
    trial_clock = core.Clock()
    visual_duration = VISUAL_FRAMES * frame_dur  # Ensure consistent duration
    soa_frames = int(abs(adjusted_soa/1000.0) / frame_dur)
    
    # Handle different trial types
    if trial_type == 'visual':
        if side == 'left':
            first_stim, second_stim = visual_stim_left, visual_stim_right
        else:
            first_stim, second_stim = visual_stim_right, visual_stim_left
        
        if soa == 0:  # Simultaneous
            # Show both stimuli for full duration
            fixation.draw()
            first_stim.draw()
            second_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Use a custom function for bilateral stimulus presentation since
            # we can't use ensure_visual_presentation with multiple stimuli
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                first_stim.draw()
                second_stim.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)  # Force clean frame rendering
        else:  # Sequential
            # First stimulus
            fixation.draw()
            first_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Use robust presentation for first stimulus
            ensure_visual_presentation(first_stim, VISUAL_FRAMES - 1, additional_stims)
            
            # Gap period if SOA > duration
            frames_gap = max(0, soa_frames - VISUAL_FRAMES)
            for frame in range(frames_gap):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip()
            
            # Second stimulus gets full duration with robust presentation
            fixation.draw()
            second_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.flip()
            
            ensure_visual_presentation(second_stim, VISUAL_FRAMES - 1, additional_stims)
    
    elif trial_type == 'auditory':
        # Stop any playing sounds
        sound_left.stop()
        sound_right.stop()
        
        if side == 'left':
            first_sound, second_sound = sound_left, sound_right
        else:
            first_sound, second_sound = sound_right, sound_left
        
        if soa == 0:  # Simultaneous
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(first_sound.play)
            win.callOnFlip(second_sound.play)
            win.flip()
            
            # Show fixation for consistent duration
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)  # Force clean frame rendering
        else:  # Sequential
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(first_sound.play)
            win.flip()
            
            # Wait for SOA with clean frame rendering
            for frame in range(soa_frames):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
            
            # Play second sound
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(second_sound.play)
            win.flip()
            
            # Show fixation for consistent duration with clean frame rendering
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
    
    elif trial_type == 'audiovisual':
        # Stop any playing sounds
        sound_left.stop()
        sound_right.stop()
        
        if side == 'left':
            visual_stim, sound_stim = visual_stim_left, sound_left
        else:
            visual_stim, sound_stim = visual_stim_right, sound_right
        
        if adjusted_soa == 0:  # Simultaneous
            # For simultaneous presentation, we separate the audio and visual
            # timing to avoid issues that can shorten the visual duration
            
            # First, reset clock but don't do anything else yet
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Now start the visual and audio together
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(sound_stim.play)
            win.flip()
            
            # Use robust presentation for remaining frames
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
                
        elif adjusted_soa < 0:  # Audio first
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(sound_stim.play)
            win.flip()
            
            # Wait for SOA with clean frame rendering
            for frame in range(soa_frames):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
            
            # Show visual for full duration using robust presentation
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES, additional_stims)
            
        else:  # Visual first
            # Start with visual using robust presentation
            fixation.draw()
            visual_stim.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(trial_clock.reset)
            win.flip()
            
            # Use robust presentation for visual stimulus
            ensure_visual_presentation(visual_stim, VISUAL_FRAMES - 1, additional_stims)
            
            # Wait additional time if SOA > visual duration
            frames_to_wait = max(0, soa_frames - VISUAL_FRAMES)
            for frame in range(frames_to_wait):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
            
            # Play audio
            fixation.draw()
            for stim in additional_stims:
                stim.draw()
            win.callOnFlip(sound_stim.play)
            win.flip()
            
            # Show fixation for consistent duration
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                for stim in additional_stims:
                    stim.draw()
                win.flip(clearBuffer=True)
    
    # Wait for response with clean frame rendering
    while not response_made:
        fixation.draw()
        for stim in additional_stims:
            stim.draw()
        win.flip(clearBuffer=True)
        
        keys = event.getKeys(timeStamped=trial_clock, keyList=['1', '2', 'escape'])
        if keys:
            if 'escape' in keys[0][0]:
                cleanup()
            else:
                rt = keys[0][1]
                response = 1 if keys[0][0] == '1' else 2
                response_made = True
                print(f"Response: {response} at {rt}s")
    
    # Stop all sounds
    sound_left.stop()
    sound_right.stop()
    return response, rt

def run_block(block_config, data_filename, config):
    exp_type = block_config['experiment'].lower()
    trials_per_condition = block_config['trials_per_condition']
    block_number = block_config['block_number']
    
    # Create experiment-specific stimuli
    if exp_type == 'srt':
        stim_color = [255, 0, 0]  # Red
        visual_stim = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in stim_color], pos=(0, 0))
        sound_stim = sound.Sound(os.path.join(os.path.dirname(__file__), "tone.wav"), secs=VISUAL_STIM_DURATION)
        total_trials = trials_per_condition * 3
        instructions = visual.TextStim(win, text="Press spacebar when you see or hear a stimulus.", color="black", pos=(0, -7), height=0.5)
        feedback = visual.TextStim(win, text="", color="black", pos=(0, -5))
        trial_types = ['visual', 'audio', 'audiovisual'] * trials_per_condition
        
    elif exp_type == 'srt_mod':
        left_color = [0, 255, 0] if block_config.get('left_visual_green', False) else [255, 0, 0]
        right_color = [255, 0, 0] if block_config.get('left_visual_green', False) else [0, 255, 0]
        visual_stim_left = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in left_color], pos=(-10, 0))
        visual_stim_right = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in right_color], pos=(10, 0))
        
        left_audio = "high" if block_config.get('left_audio_high', False) else "low"
        right_audio = "low" if block_config.get('left_audio_high', False) else "high"
        sound_left = sound.Sound(os.path.join(os.path.dirname(__file__), f"{left_audio}_pitch.wav"), secs=VISUAL_STIM_DURATION)
        sound_right = sound.Sound(os.path.join(os.path.dirname(__file__), f"{right_audio}_pitch.wav"), secs=VISUAL_STIM_DURATION)

        trial_types = (['visual_left', 'visual_right', 'visual_bilateral',
                       'audio_left', 'audio_right', 'audio_bilateral',
                       'audiovisual_left', 'audiovisual_right', 'audiovisual_bilateral']
                      * trials_per_condition)
        total_trials = len(trial_types)
        instructions = visual.TextStim(win, text="Press spacebar when you see or hear a stimulus.", color="black", pos=(0, -7), height=0.5)
        feedback = visual.TextStim(win, text="", color="black", pos=(0, -5))

    elif exp_type == 'sj':
        stim_color = [255, 0, 0]  # Red
        visual_stim = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in stim_color], pos=(0, 0))
        sound_stim = sound.Sound(os.path.join(os.path.dirname(__file__), "tone.wav"), secs=VISUAL_STIM_DURATION)
        sj_soas = [-300, -250, -200, -150, -100, -50, 0, 50, 100, 150, 200, 250, 300]
        total_trials = len(sj_soas) * trials_per_condition
        instructions = visual.TextStim(win, text="Press '1' for Same Time, '2' for Different Time", color="black", pos=(0, -7), height=0.5)
        trial_counter = visual.TextStim(win, text="", color="black", pos=(0, -8), height=0.5)
        trial_types = sj_soas * trials_per_condition
        
    elif exp_type == 'sj_mod':
        stim_color = [255, 0, 0]  # Red
        visual_stim_left = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in stim_color], pos=(-10, 0))
        visual_stim_right = visual.Circle(win, radius=stim_size/2, fillColor=[c/255 for c in stim_color], pos=(10, 0))
        sound_left = sound.Sound(os.path.join(os.path.dirname(__file__), "low_pitch.wav"), secs=VISUAL_STIM_DURATION)
        sound_right = sound.Sound(os.path.join(os.path.dirname(__file__), "high_pitch.wav"), secs=VISUAL_STIM_DURATION)
        sj_mod_soas = [-300, -200, -100, -50, 0, 50, 100, 200, 300]
        total_trials = len(sj_mod_soas) * trials_per_condition * 6  # 6 conditions
        instructions = visual.TextStim(win, text="Press '1' for Same Time, '2' for Different Time", color="black", pos=(0, -7), height=0.5)
        trial_counter = visual.TextStim(win, text="", color="black", pos=(0, -8), height=0.5)
        trial_types = [(cond, soa, side) 
                      for cond in ['visual', 'auditory', 'audiovisual']
                      for soa in sj_mod_soas
                      for side in ['left', 'right']
                      for _ in range(trials_per_condition)]

    # Prepare trials
    random.shuffle(trial_types)

    # Show instructions
    if exp_type in ['sj', 'sj_mod']:
        show_instructions("You will see a red circle and hear a tone.\n"
                        "Your task is to judge if they occurred at the same time or not.\n\n"
                        "Press '1' if they seemed to occur at the same time.\n"
                        "Press '2' if they seemed to occur at different times.\n\n"
                        "Press SPACE to begin.")
    else:
        show_instructions("Press spacebar when you see or hear a stimulus.\n\n"
                        "Press SPACE to begin.")

    best_rt = float('inf')  # Initialize best RT for SRT and SRT_Mod
    for trial_num, trial in enumerate(trial_types, 1):
        # Initialize all possible fields with default values
        participant_id = config['participant_id']
        age = config['age']
        gender = config['gender']
        site = config['site']
        trial_type = np.nan
        soa = np.nan
        side = ''
        response = np.nan
        rt = np.nan
        timestamp = core.getTime()

        if exp_type == 'sj':
            trial_counter.text = f"Trial {trial_num}/{total_trials}"
            soa = trial
            response, rt = run_sj_trial(soa, visual_stim, sound_stim, instructions, trial_counter)
            trial_type = 'audiovisual'
        elif exp_type == 'sj_mod':
            trial_counter.text = f"Trial {trial_num}/{total_trials}"
            trial_type, soa, side = trial
            response, rt = run_sj_mod_trial(trial_type, soa, side, visual_stim_left, visual_stim_right, sound_left, sound_right, instructions, trial_counter)
        elif exp_type == 'srt':
            trial_type = trial
            rt = run_srt_trial(trial_type, visual_stim, sound_stim, instructions, feedback)
            if rt is not None:
                best_rt = min(best_rt, rt)
                feedback.text = f"Block {block_number}, Trial {trial_num}/{total_trials}\nLast RT: {rt:.3f}s\nBest RT: {best_rt:.3f}s"
            else:
                feedback.text = f"Block {block_number}, Trial {trial_num}/{total_trials}\nToo fast or too slow! Invalid response."
        elif exp_type == 'srt_mod':
            trial_type = trial
            rt = run_srt_mod_trial(trial_type, visual_stim_left, visual_stim_right, sound_left, sound_right, instructions, feedback)
            if rt is not None:
                best_rt = min(best_rt, rt)
                feedback.text = f"Block {block_number}, Trial {trial_num}/{total_trials}\nLast RT: {rt:.3f}s\nBest RT: {best_rt:.3f}s"
            else:
                feedback.text = f"Block {block_number}, Trial {trial_num}/{total_trials}\nToo fast or too slow! Invalid response."

        # Save data
        trial_data = [
            participant_id, age, gender, site, block_number, trial_num, 
            trial_type, soa, side, response, rt, timestamp, exp_type
        ]
        with open(data_filename, 'a', newline='') as csvfile:
            csv.writer(csvfile).writerow(trial_data)
            csvfile.flush()

        # Check for escape key
        if event.getKeys(['escape']):
            break

    # Final message
    final_message = visual.TextStim(win, text=f"Block complete!\nThank you for participating in the {exp_type.upper()} experiment.", color="black", height=0.7)
    final_message.draw()
    win.flip()
    core.wait(3)

def run_experiment_series(config):
    """Run the experiment series with improved logging and error handling."""
    try:
        print("Starting experiment series...")
        
        # Create unique filename for data saving
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        offline_mode = config.get('offline_mode', False)
        offline_tag = "_offline" if offline_mode else ""
        data_filename = f"data_{config['participant_id']}_{config['age']}_{config['gender']}_{config['site']}{offline_tag}_{timestamp}.csv"
        print(f"Created data file: {data_filename}")

        # Prepare data file with headers
        with open(data_filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Participant_ID', 'Age', 'Gender', 'Site', 'Block_Number', 'Trial_Number', 
                              'Trial_Type', 'SOA', 'Side', 'Response', 'Reaction_Time', 'Timestamp', 'Experiment'])
        
        print(f"Starting {len(config['blocks'])} blocks...")
        for i, block in enumerate(config['blocks'], 1):
            print(f"\nRunning block {i}/{len(config['blocks'])}")
            run_block(block, data_filename, config)
            print(f"Block {i} complete")
            
            # Upload data after each block if not in offline mode
            if project and not offline_mode:
                print("\nInitiating REDCap upload...")
                if os.path.exists(data_filename):
                    upload_csv_to_redcap(data_filename)
                else:
                    print(f"Data file {data_filename} not found.")
            elif offline_mode:
                print("Running in offline mode. Data saved locally.")
            else:
                print("REDCap project not initialized. Skipping REDCap upload.")

            # Short break between blocks
            if block != config['blocks'][-1]:
                print("Waiting for participant to continue...")
                break_text = visual.TextStim(win, text=f"Take a short break.\n\nPress SPACE when you're ready to continue to the next block.", 
                                          color="black", height=0.7)
                break_text.draw()
                win.flip()
                keys = event.waitKeys(keyList=['space', 'escape'])
                if 'escape' in keys:
                    raise KeyboardInterrupt("Experiment terminated by user")

        # Experiment series complete
        print("\nAll blocks completed successfully")
        final_message = visual.TextStim(win, text="All blocks complete!\nThank you for your participation.", 
                                      color="black", height=0.7)
        final_message.draw()
        win.flip()
        core.wait(1)
        
        # Final upload to ensure everything is saved
        if project and os.path.exists(data_filename) and not offline_mode:
            print("Performing final data upload...")
            upload_success = upload_csv_to_redcap(data_filename)
            if upload_success:
                print("Final data upload successful")
            else:
                print("Final data upload failed")
        elif offline_mode:
            print("Experiment completed in offline mode. Data saved locally.")
        
        return data_filename

    except Exception as e:
        print(f"Error in run_experiment_series: {e}")
        raise
    finally:
        print("Cleaning up experiment resources...")
        # Stop individual sounds if necessary
        # Example:
        # sound_stim.stop()
        win.close()
        core.quit()

actual_fps = win.getActualFrameRate()
if actual_fps is not None:
    frame_dur = 1.0/actual_fps
else:
    frame_dur = 1.0/60.0  # Assume 60Hz if can't get actual rate
print(f"Actual frame rate: {actual_fps}")

# Function to verify if a flip occurred at the right time
def verify_visual_timing(win, target_dur):
    """Returns True if the last visual timing was acceptable"""
    return abs(win.lastFrameT - target_dur) < 0.001  # 1ms tolerance

def verify_timing_accuracy(expected_time, actual_time, tolerance=0.002):
    """Verify timing accuracy and log any issues"""
    diff = abs(actual_time - expected_time)
    if diff > tolerance:
        print(f"TIMING WARNING: Expected {expected_time}s, got {actual_time}s (diff: {diff}s)")
    return diff <= tolerance

def soa_to_frames(soa_ms, frame_duration):
    """Convert SOA in milliseconds to number of frames"""
    return round((soa_ms/1000.0) / frame_duration)

# Modify sound creation to include error handling and cleanup
def create_sound(filename, duration):
    try:
        sound_stim = sound.Sound(filename, secs=duration)
        sound_stim.setVolume(1.0)
        return sound_stim
    except Exception as e:
        print(f"Error loading sound file {filename}: {e}")
        sys.exit(1)

# Add proper cleanup
def cleanup():
    """Clean up resources properly"""
    try:
        # Stop any playing sounds
        sound.stopAllSounds()
        # Close the window
        win.close()
    finally:
        # Quit PsychoPy
        core.quit()

# Modify visual stimulus presentation to respect frame timing
def present_visual_stimulus(visual_stim, duration_frames, additional_stims=None):
    """Present a visual stimulus for a specific number of frames
    
    Returns True if successfully presented for the full duration.
    Implements robust frame timing to prevent dropped frames.
    
    Parameters:
    -----------
    visual_stim : visual.BaseVisualStim
        The primary visual stimulus to draw
    duration_frames : int
        Number of frames to display the stimulus
    additional_stims : list, optional
        List of additional visual stimuli to draw along with the main stimulus
    """
    # Ensure we have at least one frame for visibility
    duration_frames = max(1, duration_frames)
    
    # Create a clock to measure timing
    frame_clock = core.Clock()
    frame_times = []
    
    # Prepare PsychoPy for consistent timing
    # Using drawStim method for more direct control
    win.recordFrameIntervals = True
    
    # Start with the minimum elements - first frame
    fixation.draw()
    visual_stim.draw()
    
    # Draw any additional stimuli if provided
    if additional_stims:
        for stim in additional_stims:
            if stim is not None:
                stim.draw()
                
    # Reset the timer and flip
    frame_clock.reset()
    win.flip()
    frame_times.append(frame_clock.getTime())
    frames_shown = 1
    
    # Remaining frames with robust timing
    for frame in range(duration_frames - 1):
        # Critical priority: Draw visual stimulus first
        fixation.draw()
        visual_stim.draw()
        
        # Draw additional stimuli - always include them for visual timing consistency
        if additional_stims:
            for stim in additional_stims:
                if stim is not None:
                    stim.draw()
        
        # Force a proper frame update with waitBlanking=True to ensure precise timing
        win.flip(clearBuffer=True)
        curr_time = frame_clock.getTime()
        frame_times.append(curr_time)
        frames_shown += 1
        
        # Check if we're falling behind on timing and log it
        if len(frame_times) >= 2:
            last_interval = frame_times[-1] - frame_times[-2]
            if last_interval > frame_dur * 1.5:
                print(f"WARNING: Possible frame drop detected at frame {frame+1}/{duration_frames}")
    
    # Measure the actual duration
    actual_duration = frame_clock.getTime()
    expected_duration = duration_frames * frame_dur
    
    # Detailed timing analysis
    frame_intervals = [frame_times[i] - frame_times[i-1] for i in range(1, len(frame_times))]
    max_interval = max(frame_intervals) if frame_intervals else 0
    dropped_frames = sum(1 for interval in frame_intervals if interval > frame_dur * 1.5)
    
    # Always log timing information for debugging
    if dropped_frames > 0:
        print(f"TIMING WARNING: Expected {expected_duration:.4f}s, got {actual_duration:.4f}s")
        print(f"Frames requested: {duration_frames}, frames shown: {frames_shown}")
        print(f"Dropped frames: {dropped_frames}")
        print(f"Max interval: {max_interval:.4f}s (should be ~{frame_dur:.4f}s)")
        print(f"Frame intervals: {[round(i*1000) for i in frame_intervals]}ms")
    
    # Turn off frame recording to avoid memory issues
    win.recordFrameIntervals = False
    
    return dropped_frames == 0  # Return success only if no frames were dropped

def ensure_visual_presentation(visual_stim, duration_frames, additional_stims=None, max_attempts=3):
    """Ensures visual stimulus is presented properly, retrying if frames are dropped.
    
    This function is used when reliable visual presentation is critical.
    
    Parameters:
    -----------
    visual_stim : visual.BaseVisualStim
        The primary visual stimulus to draw
    duration_frames : int
        Number of frames to display the stimulus
    additional_stims : list, optional
        List of additional visual stimuli to draw along with the main stimulus
    max_attempts : int
        Maximum number of retry attempts if frames are dropped
        
    Returns:
    --------
    bool : True if presentation was successful (no dropped frames)
    """
    success = False
    attempts = 0
    
    while not success and attempts < max_attempts:
        success = present_visual_stimulus(visual_stim, duration_frames, additional_stims)
        attempts += 1
        if not success and attempts < max_attempts:
            print(f"Retrying visual presentation (attempt {attempts+1}/{max_attempts})...")
            # Short delay to let system recover before next attempt
            core.wait(0.05)
    
    if not success:
        print("WARNING: Could not achieve clean visual presentation after multiple attempts")
    
    return success

def upload_csv_to_redcap(csv_filename):
    """Upload CSV file to REDCap as a file attachment if project is available."""
    if project:
        try:
            print(f"\nAttempting to upload {csv_filename} to REDCap...")
            print(f"Using record_id: {config['participant_id']}")
            
            # First create/ensure the record exists
            record_data = [{
                'record_id': config['participant_id']
            }]
            
            try:
                # First create or update the record with just the ID
                project.import_records(record_data)
                print(f"Created/updated record for ID: {config['participant_id']}")
                
                # Now upload the file as a separate operation
                with open(csv_filename, 'rb') as file_obj:
                    file_content = file_obj.read()
                    response = project.import_file(
                        record=config['participant_id'],
                        field='python_data_file',
                        file_name=os.path.basename(csv_filename),
                        file_content=file_content
                    )
                
                print(f"Successfully uploaded {csv_filename} to REDCap")
                return True
                
            except redcap.RedcapError as e:
                print(f"REDCap API error: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error during upload: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    else:
        print("REDCap project not initialized. Skipping REDCap upload.")
        return False

# Use in run_experiment_series:
if __name__ == "__main__":
    try:
        run_experiment_series(config)
    except Exception as e:
        print(f"Error during experiment: {e}")
        cleanup()

# Check for required sound files at the start
def check_sound_files():
    required_files = ["tone.wav", "high_pitch.wav", "low_pitch.wav"]
    missing_files = []
    for filename in required_files:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)
    if missing_files:
        print(f"Missing sound files: {', '.join(missing_files)}")
        print("Launching sound_creator.py to generate missing sound files.")
        # Run sound_creator.py
        subprocess.call(["python", "sound_creator.py"])
        # After sound_creator.py exits, check again
        for filename in missing_files:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.exists(filepath):
                print(f"Error: Sound file {filename} was not created.")
                sys.exit(1)

# Call the function before running the experiment
check_sound_files()


