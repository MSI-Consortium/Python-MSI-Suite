import pandas as pd
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilenames

from analysis.sj import analyze_sj
from analysis.toj import analyze_toj
from analysis.toj_mod import analyze_toj_mod
from analysis.srt import analyze_srt

####################################################
# Analysis & Quality Control Settings
####################################################

# ---------- SJ / TOJ ----------
MIN_RESPONSE_PROPORTION = 0.10
MAX_RESPONSE_PROPORTION = 0.90

MIN_R2 = 0.80

MAX_SIGMA_MS = 500
MAX_SLOPE_MS = 500

# ---------- SRT ----------

MIN_RT_MS = 100          # Anticipation threshold
MIN_VALID_SRT_TRIALS = 250
MAX_ANTICIPATIONS = 5

MIN_MEAN_RT_SEC = 0.15
MAX_MEAN_RT_SEC = 1.50

# Create Results folder if it doesn't exist
os.makedirs("Results", exist_ok=True)

#### The analysis being done
def analyze_participant(
    df,
    participant_name,
    output_folder="Results",
    run_sj=True,
    run_toj=True,
    run_toj_mod=True,
    run_srt=True,

    # SJ / TOJ QC settings
    min_response_proportion=MIN_RESPONSE_PROPORTION,
    max_response_proportion=MAX_RESPONSE_PROPORTION,
    min_r2=MIN_R2,
    max_sigma_ms=MAX_SIGMA_MS,
    max_slope_ms=MAX_SLOPE_MS,

    # SRT QC settings
    min_rt_ms=MIN_RT_MS,
    min_valid_srt_trials=MIN_VALID_SRT_TRIALS,
    max_anticipations=MAX_ANTICIPATIONS,
    min_mean_rt_sec=MIN_MEAN_RT_SEC,
    max_mean_rt_sec=MAX_MEAN_RT_SEC
):

    # Create participant results folder
    #allows you to indicate where you want the data to be saved
    participant_folder = os.path.join(
        output_folder,
        participant_name
    )
    os.makedirs(participant_folder, exist_ok=True)

    #Separate the 3 data sets
    sj = df[df["Experiment"] == "sj"].copy()
    toj = df[df["Experiment"] == "toj"].copy()
    toj_mod = df[df["Experiment"] == "toj_mod"].copy()
    srt = df[df["Experiment"] == "srt"].copy()

    # Gives the Number of trials Per data set
    print("SJ trials:", len(sj))
    print("TOJ trials:", len(toj))
    print("TOJ_Mod trials:", len(toj_mod))
    print("SRT trials:", len(srt))

    # Extracting Participant Information
    participant_id = df["Participant_ID"].iloc[0]
    age = df["Age"].iloc[0]
    gender = df["Gender"].iloc[0]
    site = df["Site"].iloc[0]

    # ==================================================
    # SJ Analysis
    # ==================================================

    sj_available = not sj.empty

    if run_sj and sj_available:

        sj_results = analyze_sj(
            sj,
            participant_folder,
            min_r2=min_r2,
            max_sigma_ms=max_sigma_ms,
            min_response_proportion=min_response_proportion,
            max_response_proportion=max_response_proportion
        )

    elif run_sj and not sj_available:

        print(
            "SJ selected, but no SJ trials were found. "
            "Skipping SJ analysis."
        )

        sj_results = {}

    else:

        sj_results = {}

    # ==================================================
    # TOJ Analysis
    # ==================================================

    toj_available = not toj.empty

    if run_toj and toj_available:

        toj_results = analyze_toj(
            toj,
            participant_folder,
            min_r2=min_r2,
            max_slope_ms=max_slope_ms,
            min_response_proportion=min_response_proportion,
            max_response_proportion=max_response_proportion
        )

    elif run_toj and not toj_available:

        print(
            "TOJ selected, but no TOJ trials were found. "
            "Skipping TOJ analysis."
        )

        toj_results = {}

    else:

        toj_results = {}

    # ==================================================
    # TOJ_Mod Analysis
    # ==================================================

    toj_mod_available = not toj_mod.empty

    if run_toj_mod and toj_mod_available:
        toj_mod_results = analyze_toj_mod(
            toj_mod, participant_folder,
            min_r2=min_r2,
            max_slope_ms=max_slope_ms,
            min_response_proportion=min_response_proportion,
            max_response_proportion=max_response_proportion
        )
    elif run_toj_mod and not toj_mod_available:
        print("TOJ_Mod selected, but no TOJ_Mod trials were found. Skipping TOJ_Mod analysis.")
        toj_mod_results = {}
    else:
        toj_mod_results = {}

    # ==================================================
    # SRT Analysis
    # ==================================================

    srt_available = not srt.empty

    if run_srt and srt_available:

        srt_results = analyze_srt(
            srt,
            participant_folder,
            min_rt_ms=min_rt_ms,
            min_valid_trials=min_valid_srt_trials,
            max_anticipations=max_anticipations,
            min_mean_rt_sec=min_mean_rt_sec,
            max_mean_rt_sec=max_mean_rt_sec
        )

    elif run_srt and not srt_available:

        print(
            "SRT selected, but no SRT trials were found. "
            "Skipping SRT analysis."
        )

        srt_results = {}

    else:

        srt_results = {}

    # ==================================================
    # Overall Participant Quality Flag
    # ==================================================

    qc_checks = []

    # Only include SJ QC if SJ was selected
    # AND this participant actually had SJ trials.
    if run_sj and sj_available:
        qc_checks.extend([
            sj_results["SJ_Fit_OK"],
            sj_results["SJ_Response_Range_OK"],
            sj_results["SJ_Response_Bias_OK"],
            sj_results["SJ_Catch_OK"]
        ])

    # Only include TOJ QC if TOJ was selected
    # AND this participant actually had TOJ trials.
    if run_toj and toj_available:
        qc_checks.extend([
            toj_results["TOJ_Fit_OK"],
            toj_results["TOJ_Response_Range_OK"],
            toj_results["TOJ_Response_Bias_OK"],
            toj_results["TOJ_Catch_OK"]
        ])

    # Only include TOJ_Mod QC if selected and available
    if run_toj_mod and toj_mod_available:
        qc_checks.append(toj_mod_results["TOJ_Mod_QC_OK"])

    # Only include SRT QC if SRT was selected
    # AND this participant actually had SRT trials.
    if run_srt and srt_available:
        qc_checks.append(
            srt_results["SRT_QC_OK"]
        )

    # Participant passes if all analyses that were
    # actually available and analyzed passed QC.
    #
    # If no selected analyses were available,
    # leave Participant_OK undefined rather than
    # incorrectly calling the participant a PASS.
    if qc_checks:

        Participant_OK = all(
            qc_checks
        )

    else:

        Participant_OK = None

    ####################################################
    # Add participant to master results
    ####################################################
    participant_summary = {
        "Participant_ID": participant_id,
        "Source_File": participant_name,
        "Age": age,
        "Gender": gender,
        "Site": site,
        "Group": "",

        "Participant_OK": Participant_OK,

        **sj_results,
        **toj_results,
        **toj_mod_results,
        **srt_results,
    }

    return participant_summary

####################################################
# Analyze each participant
#"analyze_participant" w/ def analyze_participant directly above allows to the loop to only need to read 5 lines of cod instead of the 100+ cod that is under the :"def" that it is actually running.
def analyze_files(
    selected_files,
    output_folder="Results",
    run_sj=True,
    run_toj=True,
    run_toj_mod=True,
    run_srt=True,
    progress_callback=None,

    # SJ / TOJ QC settings
    min_response_proportion=MIN_RESPONSE_PROPORTION,
    max_response_proportion=MAX_RESPONSE_PROPORTION,
    min_r2=MIN_R2,
    max_sigma_ms=MAX_SIGMA_MS,
    max_slope_ms=MAX_SLOPE_MS,

    # SRT QC settings
    min_rt_ms=MIN_RT_MS,
    min_valid_srt_trials=MIN_VALID_SRT_TRIALS,
    max_anticipations=MAX_ANTICIPATIONS,
    min_mean_rt_sec=MIN_MEAN_RT_SEC,
    max_mean_rt_sec=MAX_MEAN_RT_SEC
):
    os.makedirs(
        output_folder,
        exist_ok=True
    )


    # Make a master-results list
    master_results = []

    total_files = len(selected_files)

    for index, file in enumerate(selected_files, start=1):
        print("\n==============================")
        print(f"Analyzing: {os.path.basename(file)}")

        if progress_callback is not None:
            progress_callback(
                index,
                total_files,
                os.path.basename(file)
            )

        participant_df = pd.read_csv(file)

        participant_name = os.path.splitext(
            os.path.basename(file)
        )[0]

        participant_results = analyze_participant(
            participant_df,
            participant_name,
            output_folder,

            run_sj=run_sj,
            run_toj=run_toj,
            run_toj_mod=run_toj_mod,
            run_srt=run_srt,

            min_response_proportion=min_response_proportion,
            max_response_proportion=max_response_proportion,
            min_r2=min_r2,
            max_sigma_ms=max_sigma_ms,
            max_slope_ms=max_slope_ms,

            min_rt_ms=min_rt_ms,
            min_valid_srt_trials=min_valid_srt_trials,
            max_anticipations=max_anticipations,
            min_mean_rt_sec=min_mean_rt_sec,
            max_mean_rt_sec=max_mean_rt_sec
        )

        master_results.append(participant_results)

    # Create master dataframe
    master_df = pd.DataFrame(master_results)

    # Save master results
    master_df.to_csv(
        os.path.join(
            output_folder,
            "Master_Results.csv"
        ),
        index=False
    )

    print("\n===================================")
    print("Master results saved!")
    print("===================================")

    print(master_df)

    return master_df

if __name__ == "__main__":

    root = Tk()
    root.withdraw()

    selected_files = askopenfilenames(
        title="Select Participant CSV Files",
        initialdir="../Data",
        filetypes=[("CSV Files", "*.csv")]
    )

    root.destroy()

    if selected_files:
        analyze_files(selected_files)