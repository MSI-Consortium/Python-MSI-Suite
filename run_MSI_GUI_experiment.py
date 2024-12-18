#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 07:48:19 2024

@author: David
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
prefs.hardware['audioLib'] = ['PTB']  # Set PTB as preferred audio engine
import numpy as np
import redcap
import subprocess  # Add this import at the top

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

# Initialize REDCap project if credentials are available
if api_url and api_token:
    project = redcap.Project(api_url, api_token)
    try:
        print("\nVerifying REDCap connection...")
        project_info = project.export_project_info()
        print(f"Connected to REDCap project: {project_info['project_title']}")
    except Exception as e:
        print(f"Error connecting to REDCap: {e}")
        project = None
else:
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


def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def save_demographic_data(config):
    """Save demographic data to CSV and create REDCap record if possible."""
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    demo_filename = f"demographic_data_{config['participant_id']}_{timestamp}.csv"
    
    # Save demographic data to CSV
    with open(demo_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['record_id', 'age', 'gender'])
        writer.writerow([config['participant_id'], config['age'], config['gender']])
    
    if project:
        # Create REDCap record
        record = {
            'record_id': config['participant_id'],
            'demographic_data_file': open(demo_filename, 'rb')
        }
        try:
            response = project.import_records([record])
            print(f"Uploaded demographic data to REDCap for participant: {config['participant_id']}")
        except Exception as e:
            print(f"Error uploading to REDCap: {e}")
            raise
        finally:
            if 'record' in locals() and hasattr(record['demographic_data_file'], 'close'):
                record['demographic_data_file'].close()
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
    """Create and configure a sound stimulus"""
    try:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        sound_stim = sound.Sound(filepath, secs=duration)
        sound_stim.setVolume(1.0)
        return sound_stim
    except Exception as e:
        print(f"Error loading sound file {filepath}: {e}")
        print("Attempting to create sound files using sound_creator.py")
        subprocess.call(["python", "sound_creator.py"])
        # Try to load the sound again
        try:
            sound_stim = sound.Sound(filepath, secs=duration)
            sound_stim.setVolume(1.0)
            return sound_stim
        except Exception as e:
            print(f"Failed to create or load sound file {filepath}: {e}")
            sys.exit(1)

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
    """
    Run a single SJ trial with proper timing for all SOA conditions.
    """
    print(f"\nStarting SJ trial with SOA: {soa}ms")
    av_sync = config.get('av_sync_correction', 0.0)
    adjusted_soa = soa + av_sync
    print(f"AV sync correction: {av_sync}ms, Adjusted SOA: {adjusted_soa}ms")
    
    response_made = False
    rt = None
    response = -1
    
    # Pre-trial setup
    fixation.draw()
    instructions.draw()
    trial_counter.draw()
    win.flip()
    core.wait(random.uniform(1, 2))  # Random foreperiod
    
    trial_clock = core.Clock()
    trial_clock.reset()
    
    # Calculate timing parameters
    visual_dur_sec = VISUAL_STIM_DURATION
    frames_per_stim = max(1, int(visual_dur_sec * actual_fps))
    soa_sec = adjusted_soa / 1000.0
    
    # For timing precision, schedule the second stimulus relative to the first
    if adjusted_soa <= 0:  # Audio first or simultaneous
        # Play audio
        sound_stim.stop()
        sound_stim.play()
        audio_onset = trial_clock.getTime()
        print(f"Audio played at {audio_onset}")
        
        # Calculate when to start visual relative to audio
        visual_start_time = abs(soa_sec)
        
        # Wait until it's time for visual, if needed
        while trial_clock.getTime() < visual_start_time:
            fixation.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
        
        # Show visual stimulus
        visual_onset = trial_clock.getTime()
        for frame in range(frames_per_stim):
            fixation.draw()
            visual_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
        visual_offset = trial_clock.getTime()
        print(f"Visual: onset={visual_onset}, offset={visual_offset}, duration={visual_offset-visual_onset}")
        
    else:  # Visual first (positive SOA)
        # Start visual stimulus
        visual_onset = trial_clock.getTime()
        
        # Calculate when audio should play relative to visual onset
        audio_target_time = visual_onset + soa_sec
        
        # Draw visual stim while monitoring for audio start time
        for frame in range(frames_per_stim):
            current_time = trial_clock.getTime()
            
            # Check if it's time to play audio
            if current_time >= audio_target_time and not sound_stim.status:
                sound_stim.play()
                print(f"Audio played at {current_time}")
            
            fixation.draw()
            visual_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
        
        visual_offset = trial_clock.getTime()
        print(f"Visual: onset={visual_onset}, offset={visual_offset}, duration={visual_offset-visual_onset}")
        
        # If audio hasn't played yet (SOA > visual duration), wait and play it
        if trial_clock.getTime() < audio_target_time:
            while trial_clock.getTime() < audio_target_time:
                fixation.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
            sound_stim.play()
            print(f"Audio played at {trial_clock.getTime()}")
    
    # Response collection phase
    response_window = 3.0  #3 second response window
    response_start = trial_clock.getTime()
    
    while (trial_clock.getTime() - response_start) < response_window and not response_made:
        fixation.draw()
        instructions.draw()
        trial_counter.draw()
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
    
    # Pre-trial setup
    fixation.draw()
    feedback.draw()
    win.flip()
    foreperiod = random.uniform(1, 3)
    print(f"Waiting foreperiod: {foreperiod}s")
    core.wait(foreperiod)
    
    # Calculate fixed stimulus duration
    stimulus_duration = VISUAL_STIM_DURATION
    if actual_fps is None:
        assumed_fps = 60.0
        stimulus_frames = max(1, int(stimulus_duration * assumed_fps))
        print(f"Using assumed refresh rate of {assumed_fps}Hz")
    else:
        stimulus_frames = max(1, int(stimulus_duration * actual_fps))
    print(f"Stimulus duration: {stimulus_duration}s ({stimulus_frames} frames)")
    
    trial_clock = core.Clock()
    trial_clock.reset()
    stim_onset = None
    
    # Present stimulus
    if trial_type == 'audiovisual':
        print(f"Starting AV stimulus with {av_sync}ms offset")
        if av_sync <= 0:  # Audio first or simultaneous
            sound_stim.stop()
            
            if av_sync == 0:  # Truly simultaneous
                # Present both stimuli for full duration
                fixation.draw()
                visual_stim.draw()
                feedback.draw()
                win.callOnFlip(sound_stim.play)
                win.flip()
                stim_onset = trial_clock.getTime()
                print(f"Simultaneous AV onset at {stim_onset}")
                
                # Maintain visual stimulus for full duration
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    visual_stim.draw()
                    feedback.draw()
                    win.flip()
                
            else:  # Audio leads
                print("Playing audio")
                sound_stim.play()
                wait_time = abs(av_sync)/1000.0
                print(f"Waiting {wait_time}s before visual")
                
                # Show fixation during wait
                wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
                for frame in range(wait_frames):
                    fixation.draw()
                    feedback.draw()
                    win.flip()
                
                # Then show visual for fixed duration
                print("Starting visual presentation")
                fixation.draw()
                visual_stim.draw()
                feedback.draw()
                win.flip()
                stim_onset = trial_clock.getTime()
                
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    visual_stim.draw()
                    feedback.draw()
                    win.flip()
                print(f"Visual presentation complete at {trial_clock.getTime() - stim_onset}s")
                
        else:  # Visual first (positive asynchrony)
            # Present visual for fixed duration
            print("Starting visual presentation")
            fixation.draw()
            visual_stim.draw()
            feedback.draw()
            win.flip()
            stim_onset = trial_clock.getTime()
            
            for frame in range(stimulus_frames-1):
                fixation.draw()
                visual_stim.draw()
                feedback.draw()
                win.flip()
                
            # Show fixation during delay before audio
            wait_time = av_sync/1000.0
            wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
            print(f"Adding {wait_frames} delay frames before audio")
            
            for frame in range(wait_frames):
                fixation.draw()
                feedback.draw()
                win.flip()
            
            sound_stim.stop()
            sound_stim.play()
            print("Playing audio")
            
    elif trial_type == 'visual':
        print("Starting visual stimulus")
        fixation.draw()
        visual_stim.draw()
        feedback.draw()
        win.flip()
        stim_onset = trial_clock.getTime()
        
        for frame in range(stimulus_frames-1):
            fixation.draw()
            visual_stim.draw()
            feedback.draw()
            win.flip()
            
    else:  # audio
        print("Starting audio stimulus")
        sound_stim.stop()
        sound_stim.play()
        stim_onset = trial_clock.getTime()
        
        for frame in range(stimulus_frames):
            fixation.draw()
            feedback.draw()
            win.flip()
    
    # Clear stimulus and wait for response
    response_window = 2.0  # Allow 2 seconds for response
    
    while (trial_clock.getTime() - stim_onset) < response_window and not response_made:
        fixation.draw()
        feedback.draw()
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
    
    # End trial
    fixation.draw()
    feedback.draw()
    win.flip()
    sound_stim.stop()
    
    end_time = trial_clock.getTime()
    print(f"Trial duration: {end_time - stim_onset}s")
    
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
    
    # Pre-trial setup
    fixation.draw()
    feedback.draw()
    win.flip()
    foreperiod = random.uniform(1, 3)
    print(f"Waiting foreperiod: {foreperiod}s")
    core.wait(foreperiod)
    
    # Calculate fixed stimulus duration
    stimulus_duration = VISUAL_STIM_DURATION
    if actual_fps is None:
        assumed_fps = 60.0
        stimulus_frames = max(1, int(stimulus_duration * assumed_fps))
        print(f"Using assumed refresh rate of {assumed_fps}Hz")
    else:
        stimulus_frames = max(1, int(stimulus_duration * actual_fps))
    print(f"Stimulus duration: {stimulus_duration}s ({stimulus_frames} frames)")
    
    trial_clock = core.Clock()
    trial_clock.reset()
    stim_onset = None

    def draw_visual_stimuli():
        if '_left' in trial_type:
            visual_stim_left.draw()
        elif '_right' in trial_type:
            visual_stim_right.draw()
        elif '_bilateral' in trial_type:
            visual_stim_left.draw()
            visual_stim_right.draw()
    
    def play_audio():
        if '_left' in trial_type:
            sound_left.play()
        elif '_right' in trial_type:
            sound_right.play()
        elif '_bilateral' in trial_type:
            sound_left.play()
            sound_right.play()
    
    # Present stimulus
    if 'audiovisual' in trial_type:
        print(f"Starting AV stimulus with {av_sync}ms offset")
        if av_sync <= 0:  # Audio first or simultaneous
            if av_sync == 0:  # Truly simultaneous
                # Present both stimuli for full duration
                fixation.draw()
                draw_visual_stimuli()
                feedback.draw()
                win.callOnFlip(play_audio)
                win.flip()
                stim_onset = trial_clock.getTime()
                print(f"Simultaneous AV onset at {stim_onset}")
                
                # Maintain visual stimulus for full duration
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    draw_visual_stimuli()
                    feedback.draw()
                    win.flip()
            
            else:  # Audio leads
                print("Playing audio")
                play_audio()
                wait_time = abs(av_sync)/1000.0
                print(f"Waiting {wait_time}s before visual")
                
                # Show fixation during wait
                wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
                for frame in range(wait_frames):
                    fixation.draw()
                    feedback.draw()
                    win.flip()
                
                # Then show visual for fixed duration
                print("Starting visual presentation")
                fixation.draw()
                draw_visual_stimuli()
                feedback.draw()
                win.flip()
                stim_onset = trial_clock.getTime()
                
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    draw_visual_stimuli()
                    feedback.draw()
                    win.flip()
                print(f"Visual presentation complete at {trial_clock.getTime() - stim_onset}s")
                
        else:  # Visual first (positive asynchrony)
            # Present visual for fixed duration
            print("Starting visual presentation")
            fixation.draw()
            draw_visual_stimuli()
            feedback.draw()
            win.flip()
            stim_onset = trial_clock.getTime()
            
            for frame in range(stimulus_frames-1):
                fixation.draw()
                draw_visual_stimuli()
                feedback.draw()
                win.flip()
            
            # Show fixation during delay before audio
            wait_time = av_sync/1000.0
            wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
            print(f"Adding {wait_frames} delay frames before audio")
            
            for frame in range(wait_frames):
                fixation.draw()
                feedback.draw()
                win.flip()
            
            play_audio()
            print("Playing audio")
            
    elif 'visual' in trial_type:
        print("Starting visual stimulus")
        fixation.draw()
        draw_visual_stimuli()
        feedback.draw()
        win.flip()
        stim_onset = trial_clock.getTime()
        
        for frame in range(stimulus_frames-1):
            fixation.draw()
            draw_visual_stimuli()
            feedback.draw()
            win.flip()
            
    else:  # audio only trials
        print("Starting audio stimulus")
        play_audio()
        stim_onset = trial_clock.getTime()
        
        for frame in range(stimulus_frames):
            fixation.draw()
            feedback.draw()
            win.flip()
    
    # Clear stimulus and wait for response
    response_window = 2.0  # Allow 2 seconds for response
    
    while (trial_clock.getTime() - stim_onset) < response_window and not response_made:
        fixation.draw()
        feedback.draw()
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
    
    # End trial
    fixation.draw()
    feedback.draw()
    win.flip()
    
    end_time = trial_clock.getTime()
    print(f"Trial duration: {end_time - stim_onset}s")
    
    if rt is not None and rt < 0.05:
        print("Response too fast")
        return None
    
    return rt

def run_sj_mod_trial(trial_type, soa, side, visual_stim_left, visual_stim_right, sound_left, sound_right, instructions, trial_counter):
    print(f"\nStarting SJ_Mod trial: {trial_type}, SOA: {soa}ms, Side: {side}")
    av_sync = config.get('av_sync_correction', 0.0)
    print(f"AV sync correction: {av_sync}ms")
    response_made = False
    rt = None
    response = -1
    
    # Pre-trial setup
    fixation.draw()
    instructions.draw()
    trial_counter.draw()
    win.flip()
    foreperiod = random.uniform(1, 2)
    print(f"Waiting foreperiod: {foreperiod}s")
    core.wait(foreperiod)
    
    # Calculate fixed stimulus duration
    stimulus_duration = VISUAL_STIM_DURATION
    if actual_fps is None:
        assumed_fps = 60.0
        stimulus_frames = max(1, int(stimulus_duration * assumed_fps))
        print(f"Using assumed refresh rate of {assumed_fps}Hz")
    else:
        stimulus_frames = max(1, int(stimulus_duration * actual_fps))
    print(f"Stimulus duration: {stimulus_duration}s ({stimulus_frames} frames)")
    
    trial_clock = core.Clock()
    trial_clock.reset()
    stim_onset = None
    
    if trial_type == 'visual':
        if side == 'left':
            first_stim, second_stim = visual_stim_left, visual_stim_right
        else:
            first_stim, second_stim = visual_stim_right, visual_stim_left
        
        if soa == 0:  # Simultaneous
            fixation.draw()
            first_stim.draw()
            second_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
            stim_onset = trial_clock.getTime()
            
            # Maintain visual stimulus for full duration
            for frame in range(stimulus_frames-1):
                fixation.draw()
                first_stim.draw()
                second_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
        else:  # Sequential
            # First stimulus
            fixation.draw()
            first_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
            stim_onset = trial_clock.getTime()
            
            for frame in range(stimulus_frames-1):
                fixation.draw()
                first_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
            
            # Wait for SOA
            wait_time = abs(soa/1000.0)
            wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
            for frame in range(wait_frames):
                fixation.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
            
            # Second stimulus
            fixation.draw()
            second_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
            
            for frame in range(stimulus_frames-1):
                fixation.draw()
                second_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
            
    elif trial_type == 'auditory':
        if side == 'left':
            first_sound, second_sound = sound_left, sound_right
        else:
            first_sound, second_sound = sound_right, sound_left
            
        first_sound.stop()
        second_sound.stop()
        
        if soa == 0:  # Simultaneous
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(first_sound.play)
            win.callOnFlip(second_sound.play)
            win.flip()
            stim_onset = trial_clock.getTime()
        else:  # Sequential
            win.callOnFlip(trial_clock.reset)
            win.callOnFlip(first_sound.play)
            win.flip()
            stim_onset = trial_clock.getTime()
            core.wait(abs(soa/1000.0))
            second_sound.play()
            
    elif trial_type == 'audiovisual':
        adjusted_soa = soa + av_sync
        if side == 'left':
            visual_stim, sound_stim = visual_stim_left, sound_left
        else:
            visual_stim, sound_stim = visual_stim_right, sound_right
            
        sound_stim.stop()
        
        if adjusted_soa <= 0:  # Audio first or simultaneous
            if adjusted_soa == 0:  # Truly simultaneous
                fixation.draw()
                visual_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.callOnFlip(sound_stim.play)
                win.flip()
                stim_onset = trial_clock.getTime()
                
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    visual_stim.draw()
                    instructions.draw()
                    trial_counter.draw()
                    win.flip()
            else:  # Audio leads
                sound_stim.play()
                wait_time = abs(adjusted_soa/1000.0)
                wait_frames = int(wait_time * actual_fps if actual_fps else wait_time * 60.0)
                for frame in range(wait_frames):
                    fixation.draw()
                    instructions.draw()
                    trial_counter.draw()
                    win.flip()
                
                fixation.draw()
                visual_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
                stim_onset = trial_clock.getTime()
                
                for frame in range(stimulus_frames-1):
                    fixation.draw()
                    visual_stim.draw()
                    instructions.draw()
                    trial_counter.draw()
                    win.flip()
        else:  # Visual first
            fixation.draw()
            visual_stim.draw()
            instructions.draw()
            trial_counter.draw()
            win.flip()
            stim_onset = trial_clock.getTime()
            
            for frame in range(stimulus_frames-1):
                fixation.draw()
                visual_stim.draw()
                instructions.draw()
                trial_counter.draw()
                win.flip()
            
            wait_time = adjusted_soa/1000.0
            core.wait(wait_time)
            sound_stim.play()
    
    # Response collection
    response_window = 2.0
    while (trial_clock.getTime() - stim_onset) < response_window and not response_made:
        fixation.draw()
        instructions.draw()
        trial_counter.draw()
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
        data_filename = f"data_{config['participant_id']}_{config['age']}_{config['gender']}_{config['site']}_{timestamp}.csv"
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
            
            # Upload data after each block
            if project:
                print("\nInitiating REDCap upload...")
                if os.path.exists(data_filename):
                    upload_csv_to_redcap(data_filename)
                else:
                    print(f"Data file {data_filename} not found.")
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
        print("Performing final data upload...")
        if project and os.path.exists(data_filename):
            upload_success = upload_csv_to_redcap(data_filename)
            if upload_success:
                print("Final data upload successful")
            else:
                print("Final data upload failed")
        
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
def present_visual_stimulus(visual_stim, duration_frames):
    """Present a visual stimulus for a specific number of frames"""
    for frame in range(duration_frames):
        visual_stim.draw()
        win.flip()
    return True

def upload_csv_to_redcap(csv_filename):
    """Upload CSV file to REDCap as a file attachment if project is available."""
    if project:
        try:
            print(f"\nAttempting to upload {csv_filename} to REDCap...")
            print(f"Using record_id: {config['participant_id']}")
            
            # Create a record with the file
            record = {
                'record_id': config['participant_id'],
                'python_data_file': open(csv_filename, 'rb')
            }

            print("Record created, attempting import...")
            try:
                response = project.import_records([record])
                print(f"Raw REDCap response: {response}")
                
                if response and response.get('count') == 1:
                    print(f"Successfully uploaded {csv_filename} to REDCap")
                    return True
                else:
                    print(f"Upload failed - unexpected response: {response}")
                    return False
                    
            except redcap.RedcapError as e:
                print(f"REDCap API error: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error during upload: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(traceback.format_exc())
            return False
        finally:
            # Ensure file is closed
            if 'record' in locals() and hasattr(record['python_data_file'], 'close'):
                record['python_data_file'].close()
                print("File handle closed")
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
