#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Timing Verification Script for AV Sync Calibration

This script presents audiovisual stimuli with known timing offsets for verification
with an oscilloscope using a photodiode (for visual) and microphone (for audio).

Usage:
    python timing_verification.py

Controls:
    SPACE - Present stimulus
    R     - Toggle repeat mode (continuous presentation for oscilloscope triggering)
    N     - Next condition
    C     - Enter correction value to test
    Q/ESC - Quit

For calibration:
    1. Connect photodiode to oscilloscope channel 1 (visual signal)
    2. Connect microphone to oscilloscope channel 2 (audio signal)
    3. Trigger on the visual signal (rising edge)
    4. Measure the time difference between visual and audio onsets
    5. The measured offset should match the displayed av_sync value
    6. If there's a consistent offset, press C and enter a correction to test

@author: David Tovar / Claude
"""

import platform
import os
import sys
from psychopy import visual, core, event, monitors, sound
from psychopy import prefs

# Configure audio settings before importing sound
prefs.hardware['audioLib'] = ['PTB']
prefs.general['audioDevice'] = 'default'

# Initialize sound system (not available in all PsychoPy versions)
try:
    sound.init()
except AttributeError:
    pass  # Sound system initializes automatically when creating Sound objects

# Try to import psychtoolbox for precise audio scheduling
PTB_AVAILABLE = False
try:
    import psychtoolbox as ptb
    PTB_AVAILABLE = True
    print("PTB prescheduling: Available (sub-ms precision)")
except ImportError:
    print("PTB prescheduling: Not available (using callOnFlip fallback ~5ms precision)")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Test conditions: av_sync values in milliseconds
# Positive = visual first, Negative = audio first, Zero = simultaneous
TEST_CONDITIONS = [
    {'av_sync': 0, 'label': 'SIMULTANEOUS (0ms)'},
    {'av_sync': 50, 'label': 'VISUAL FIRST (+50ms)'},
    {'av_sync': 100, 'label': 'VISUAL FIRST (+100ms)'},
    {'av_sync': 150, 'label': 'VISUAL FIRST (+150ms)'},
    {'av_sync': -50, 'label': 'AUDIO FIRST (-50ms)'},
    {'av_sync': -100, 'label': 'AUDIO FIRST (-100ms)'},
    {'av_sync': -150, 'label': 'AUDIO FIRST (-150ms)'},
    {'av_sync': 200, 'label': 'VISUAL FIRST (+200ms)'},
    {'av_sync': -200, 'label': 'AUDIO FIRST (-200ms)'},
]

# Timing parameters
VISUAL_STIM_DURATION = 0.1  # seconds (100ms)
INTER_TRIAL_INTERVAL = 1.0  # seconds between presentations in repeat mode

# Window parameters
WIN_WIDTH = 1000
WIN_HEIGHT = 700

# ============================================================================
# PLATFORM-SPECIFIC SETTINGS
# ============================================================================

RUNNING_ON_MAC = platform.system() == 'Darwin'

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

# ============================================================================
# TIMING UTILITIES
# ============================================================================

def calculate_soa_frames(soa_ms, frame_dur):
    """Convert SOA in milliseconds to number of frames with consistent rounding."""
    return max(0, round(abs(soa_ms / 1000.0) / frame_dur))


def get_reliable_framerate(win, fallback_fps=60.0):
    """Get reliable framerate with multiple fallback methods.

    Uses multiple detection strategies:
    1. getActualFrameRate() with relaxed parameters
    2. getMsPerFrame() as backup (measures over 60+ frames)
    3. Fallback to specified fps if all methods fail
    """
    print("\nMeasuring monitor refresh rate...")

    # Method 1: Try getActualFrameRate with relaxed parameters
    try:
        fps = win.getActualFrameRate(
            nIdentical=10,
            nMaxFrames=100,
            nWarmUpFrames=20,
            threshold=2  # Relaxed threshold
        )
        if fps and 30 <= fps <= 240:
            print(f"Method 1 (getActualFrameRate): {fps:.2f} Hz")
            return fps
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: Try getMsPerFrame (more robust)
    try:
        print("Trying alternative method (getMsPerFrame)...")
        timing_stats = win.getMsPerFrame(nFrames=60, showVisual=False)
        if timing_stats and len(timing_stats) >= 1:
            avg_ms = timing_stats[0]
            if avg_ms and 4 <= avg_ms <= 40:
                fps = 1000.0 / avg_ms
                std_ms = timing_stats[1] if len(timing_stats) > 1 else 0
                print(f"Method 2 (getMsPerFrame): {fps:.2f} Hz (avg: {avg_ms:.2f}ms, std: {std_ms:.2f}ms)")
                if std_ms > 2:
                    print(f"  WARNING: High frame timing variability. V-sync may be off.")
                return fps
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # Method 3: Try monitor configuration
    try:
        mon_fps = win.monitorFramePeriod
        if mon_fps and mon_fps > 0:
            fps = 1.0 / mon_fps
            if 30 <= fps <= 240:
                print(f"Method 3 (monitorFramePeriod): {fps:.2f} Hz")
                return fps
    except Exception as e:
        print(f"Method 3 failed: {e}")

    print(f"All methods failed. Using fallback: {fallback_fps} Hz")
    return fallback_fps


def schedule_sound_at_flip(win, sound_stim, delay_seconds=0.0):
    """
    Schedule a sound to play at a precise time using PTB prescheduling.

    PTB prescheduling allows the audio system to prepare buffers in advance,
    resulting in sub-ms precision instead of ~5ms with callOnFlip.

    Parameters:
    -----------
    win : visual.Window
        The PsychoPy window (needed for getFutureFlipTime)
    sound_stim : sound.Sound
        The sound stimulus to schedule
    delay_seconds : float
        Additional delay after the next flip (in seconds)

    Returns:
    --------
    bool : True if prescheduling was used, False if falling back to callOnFlip
    """
    if not PTB_AVAILABLE or sound_stim is None:
        return False

    try:
        # Get the time of the next screen flip in PTB clock format
        next_flip_time = win.getFutureFlipTime(clock='ptb')

        if next_flip_time is None:
            return False

        # Calculate target audio onset time
        target_time = next_flip_time + delay_seconds

        # Schedule the sound to play at exactly that time
        sound_stim.play(when=target_time)
        return True

    except Exception as e:
        print(f"PTB prescheduling failed: {e}, using callOnFlip fallback")
        return False


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def get_audio_lib_name():
    """Get audio library name, handling different PsychoPy versions."""
    try:
        return sound.audioLib
    except AttributeError:
        return prefs.hardware['audioLib']

def main():
    print("\n" + "=" * 60)
    print("TIMING VERIFICATION SCRIPT")
    print("=" * 60)
    print(f"Platform: {'Mac' if RUNNING_ON_MAC else 'Windows/Linux'}")
    print(f"Audio library: {get_audio_lib_name()}")
    print("=" * 60)

    # Set up monitor
    mon = monitors.Monitor('testMonitor')
    mon.setWidth(32)
    mon.setDistance(57)
    mon.setSizePix((WIN_WIDTH, WIN_HEIGHT))

    # Create window
    win = visual.Window(
        [WIN_WIDTH, WIN_HEIGHT],
        color=[1, 1, 1],  # White background
        units="deg",
        monitor=mon,
        **WINDOW_CONFIG
    )

    # Get frame rate
    actual_fps = get_reliable_framerate(win)
    frame_dur = 1.0 / actual_fps
    VISUAL_FRAMES = max(1, int(VISUAL_STIM_DURATION * actual_fps))

    print(f"Frame duration: {frame_dur * 1000:.2f} ms")
    print(f"Frames per stimulus: {VISUAL_FRAMES}")
    print("=" * 60)

    # Create stimuli
    # Visual: Large red circle for high contrast photodiode detection
    visual_stim = visual.Circle(
        win,
        radius=3,
        fillColor='red',
        lineColor='red',
        pos=(0, 0)
    )

    # Dotted circle outline showing where stimulus will appear
    # (helps position photodiode before stimulus presentation)
    stim_outline = visual.Circle(
        win,
        radius=3,
        fillColor=None,
        lineColor='gray',
        lineWidth=2,
        pos=(0, 0),
        edges=64
    )
    # Create dashed effect with multiple small circles
    outline_dots = []
    import math
    num_dots = 24
    for i in range(num_dots):
        angle = (2 * math.pi * i) / num_dots
        x = 3 * math.cos(angle)
        y = 3 * math.sin(angle)
        dot = visual.Circle(
            win,
            radius=0.15,
            fillColor='lightgray',
            lineColor='lightgray',
            pos=(x, y)
        )
        outline_dots.append(dot)

    # Fixation cross
    fixation = visual.ShapeStim(
        win,
        vertices=((0, -0.5), (0, 0.5), (0, 0), (-0.5, 0), (0.5, 0)),
        lineWidth=5,
        closeShape=False,
        lineColor="black"
    )

    # Load sound
    sound_file = os.path.join(os.path.dirname(__file__), "tone.wav")
    if not os.path.exists(sound_file):
        print("Sound file not found. Creating...")
        import subprocess
        subprocess.call([sys.executable, "sound_creator.py"])

    sound_stim = sound.Sound(sound_file, secs=VISUAL_STIM_DURATION)
    sound_stim.setVolume(0.8)

    # Text displays
    title_text = visual.TextStim(
        win,
        text="TIMING VERIFICATION",
        color="black",
        height=0.8,
        pos=(0, 8)
    )

    condition_text = visual.TextStim(
        win,
        text="",
        color="black",
        height=0.7,
        pos=(0, 6)
    )

    info_text = visual.TextStim(
        win,
        text="",
        color="gray",
        height=0.4,
        pos=(0, -6)
    )

    instructions_text = visual.TextStim(
        win,
        text="SPACE=present | R=repeat | N=next | C=set correction | 0=clear correction | Q=quit",
        color="gray",
        height=0.35,
        pos=(0, -8)
    )

    mode_text = visual.TextStim(
        win,
        text="",
        color="blue",
        height=0.4,
        pos=(0, -7)
    )

    correction_text = visual.TextStim(
        win,
        text="",
        color="darkgreen",
        height=0.5,
        pos=(0, 4)
    )

    input_prompt = visual.TextStim(
        win,
        text="",
        color="black",
        height=0.6,
        pos=(0, 0)
    )

    input_value_text = visual.TextStim(
        win,
        text="",
        color="blue",
        height=0.8,
        pos=(0, -1.5)
    )

    # State variables
    current_condition_idx = 0
    repeat_mode = False
    running = True
    trial_clock = core.Clock()
    applied_correction = 0.0  # User-entered correction to test
    input_mode = False  # Whether we're in text input mode
    input_buffer = ""  # Buffer for text input

    def present_av_stimulus(av_sync_ms, correction_ms=0):
        """Present audiovisual stimulus with specified AV sync offset using frame-based timing.

        Uses PTB prescheduling when available for sub-ms audio timing precision.

        Args:
            av_sync_ms: Base AV sync value from test condition
            correction_ms: User-entered correction to apply (added to av_sync_ms)
        """
        nonlocal trial_clock

        # Apply correction to the av_sync value
        total_av_sync = av_sync_ms + correction_ms

        if total_av_sync == 0:
            # Simultaneous: present visual and audio together
            fixation.draw()
            visual_stim.draw()
            win.callOnFlip(trial_clock.reset)

            # Try PTB prescheduling for sub-ms precision
            if not schedule_sound_at_flip(win, sound_stim, delay_seconds=0.0):
                win.callOnFlip(sound_stim.play)
            win.flip()

            # Continue visual presentation
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                visual_stim.draw()
                win.flip()

        elif total_av_sync > 0:
            # Visual first (positive): show visual, wait, then play audio
            # Calculate total delay for audio: visual frames + wait frames
            wait_frames = calculate_soa_frames(total_av_sync, frame_dur)
            total_audio_delay = (VISUAL_FRAMES + wait_frames) * frame_dur

            fixation.draw()
            visual_stim.draw()
            win.callOnFlip(trial_clock.reset)

            # Try to preschedule audio at the calculated future time
            prescheduled = False
            if total_audio_delay > 0.01:  # Only preschedule if delay > 10ms
                prescheduled = schedule_sound_at_flip(win, sound_stim, delay_seconds=total_audio_delay)
            win.flip()

            # Continue visual presentation
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                visual_stim.draw()
                win.flip()

            # Wait for audio onset using frame-based timing
            for frame in range(wait_frames):
                fixation.draw()
                win.flip()

            # If prescheduling wasn't used, play audio now
            if not prescheduled:
                win.callOnFlip(sound_stim.play)
                win.flip()

            # Wait for audio to finish playing (same duration as visual stimulus)
            for frame in range(VISUAL_FRAMES):
                fixation.draw()
                win.flip()

        else:
            # Audio first (negative): play audio, wait, then show visual
            fixation.draw()
            win.callOnFlip(trial_clock.reset)

            # Try PTB prescheduling for audio onset
            if not schedule_sound_at_flip(win, sound_stim, delay_seconds=0.0):
                win.callOnFlip(sound_stim.play)
            win.flip()

            # Wait for visual onset using frame-based timing
            wait_frames = calculate_soa_frames(abs(total_av_sync), frame_dur)
            for frame in range(wait_frames):
                fixation.draw()
                win.flip()

            # Show visual
            fixation.draw()
            visual_stim.draw()
            win.flip()

            # Continue visual presentation
            for frame in range(VISUAL_FRAMES - 1):
                fixation.draw()
                visual_stim.draw()
                win.flip()

        # Clear screen - show outline dots again
        for dot in outline_dots:
            dot.draw()
        fixation.draw()
        win.flip()

        # Stop sound
        sound_stim.stop()

    def draw_screen():
        """Draw the current state to the screen."""
        condition = TEST_CONDITIONS[current_condition_idx]

        # Draw dotted outline showing where stimulus will appear
        for dot in outline_dots:
            dot.draw()

        title_text.draw()
        condition_text.text = f"Condition {current_condition_idx + 1}/{len(TEST_CONDITIONS)}: {condition['label']}"
        condition_text.draw()

        # Show correction if applied
        if applied_correction != 0:
            total = condition['av_sync'] + applied_correction
            correction_text.text = f"CORRECTION: {applied_correction:+.0f}ms applied | Effective av_sync: {total:+.0f}ms"
            correction_text.draw()

        av_sync = condition['av_sync']
        effective_sync = av_sync + applied_correction

        if effective_sync > 0:
            timing_desc = f"Visual appears {abs(effective_sync):.0f}ms BEFORE audio"
        elif effective_sync < 0:
            timing_desc = f"Audio plays {abs(effective_sync):.0f}ms BEFORE visual"
        else:
            timing_desc = "Visual and audio are simultaneous"

        base_info = f"Base: {av_sync}ms"
        if applied_correction != 0:
            base_info += f" + Correction: {applied_correction:+.0f}ms = {effective_sync:+.0f}ms"

        info_text.text = f"{timing_desc}\n({base_info}, {calculate_soa_frames(effective_sync, frame_dur)} frames at {actual_fps:.1f}Hz)"
        info_text.draw()

        mode_text.text = "MODE: REPEAT (continuous)" if repeat_mode else "MODE: MANUAL (press SPACE to present)"
        mode_text.draw()

        instructions_text.draw()
        fixation.draw()
        win.flip()

    def draw_input_screen():
        """Draw the correction input screen."""
        # Draw dotted outline
        for dot in outline_dots:
            dot.draw()

        title_text.draw()

        input_prompt.text = "Enter correction value in ms\n(negative = shift audio earlier, positive = shift visual earlier)\nPress ENTER to confirm, ESC to cancel"
        input_prompt.draw()

        input_value_text.text = input_buffer if input_buffer else "0"
        input_value_text.draw()

        fixation.draw()
        win.flip()

    # Main loop
    print("\nStarting verification loop...")
    print("Press SPACE to present stimulus, R to toggle repeat mode, N for next condition")
    print("Press C to enter correction value, 0 to clear correction, Q to quit")

    last_presentation_time = 0

    while running:
        if input_mode:
            # Input mode: collecting correction value
            draw_input_screen()

            keys = event.getKeys()
            for key in keys:
                if key == 'escape':
                    # Cancel input
                    input_mode = False
                    input_buffer = ""
                    print("Correction input cancelled")

                elif key == 'return':
                    # Confirm input
                    try:
                        if input_buffer == "" or input_buffer == "-":
                            applied_correction = 0.0
                        else:
                            applied_correction = float(input_buffer)
                        print(f"Correction set to: {applied_correction:+.0f}ms")
                    except ValueError:
                        print(f"Invalid input: '{input_buffer}', correction unchanged")
                    input_mode = False
                    input_buffer = ""

                elif key == 'backspace':
                    input_buffer = input_buffer[:-1]

                elif key == 'minus' or key == 'num_subtract':
                    if len(input_buffer) == 0:
                        input_buffer = "-"

                elif key == 'period' or key == 'num_decimal':
                    if '.' not in input_buffer:
                        input_buffer += "."

                elif key in '0123456789':
                    input_buffer += key

                elif key.startswith('num_') and key[-1] in '0123456789':
                    input_buffer += key[-1]

        else:
            # Normal mode
            draw_screen()

            # Check for key presses
            keys = event.getKeys()

            for key in keys:
                if key in ['q', 'escape']:
                    running = False

                elif key == 'r':
                    repeat_mode = not repeat_mode
                    print(f"Repeat mode: {'ON' if repeat_mode else 'OFF'}")

                elif key == 'n':
                    current_condition_idx = (current_condition_idx + 1) % len(TEST_CONDITIONS)
                    print(f"Switched to condition {current_condition_idx + 1}: {TEST_CONDITIONS[current_condition_idx]['label']}")

                elif key == 'c':
                    # Enter correction input mode
                    input_mode = True
                    input_buffer = ""
                    repeat_mode = False  # Pause repeat mode during input
                    print("Enter correction value (ms)...")

                elif key == '0' and not input_mode:
                    # Quick clear correction
                    applied_correction = 0.0
                    print("Correction cleared (set to 0ms)")

                elif key == 'space':
                    condition = TEST_CONDITIONS[current_condition_idx]
                    effective = condition['av_sync'] + applied_correction
                    if applied_correction != 0:
                        print(f"Presenting: {condition['label']} + correction {applied_correction:+.0f}ms = {effective:+.0f}ms effective")
                    else:
                        print(f"Presenting: {condition['label']} (av_sync={condition['av_sync']}ms)")
                    present_av_stimulus(condition['av_sync'], applied_correction)
                    last_presentation_time = core.getTime()

            # Auto-present in repeat mode
            if repeat_mode and (core.getTime() - last_presentation_time) > INTER_TRIAL_INTERVAL:
                condition = TEST_CONDITIONS[current_condition_idx]
                effective = condition['av_sync'] + applied_correction
                if applied_correction != 0:
                    print(f"[REPEAT] {condition['label']} + correction {applied_correction:+.0f}ms = {effective:+.0f}ms")
                else:
                    print(f"[REPEAT] Presenting: {condition['label']} (av_sync={condition['av_sync']}ms)")
                present_av_stimulus(condition['av_sync'], applied_correction)
                last_presentation_time = core.getTime()

        core.wait(0.01)  # Small delay to reduce CPU usage

    # Cleanup
    print("\nClosing...")
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
