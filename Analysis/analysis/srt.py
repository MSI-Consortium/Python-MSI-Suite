import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def analyze_srt(
    srt,
    participant_folder,
    min_rt_ms=100,
    min_valid_trials=250,
    max_anticipations=5,
    min_mean_rt_sec=0.15,
    max_mean_rt_sec=1.50
):
    """
    Analyze Simple Reaction Time data for one participant.

    Uses Adjusted_RT for all reaction-time calculations.

    Return  a dictionary containing SRT results and QC measures.
    """

    # --------------------------------
    # Trial counts
    # --------------------------------
    srt = srt.copy()
    srt_trials = len(srt)

    # Keep trials containing an Adjusted_RT
    srt_valid = srt.dropna(
        subset=["Adjusted_RT"]
    ).copy()

    srt_valid_trials = len(srt_valid)

    srt_misses = srt_trials - srt_valid_trials

    # --------------------------------
    # Anticipatory responses
    # --------------------------------

    anticipation_threshold = min_rt_ms / 1000

    anticipations = srt_valid[
        srt_valid["Adjusted_RT"] < anticipation_threshold
    ]

    n_anticipations = len(anticipations)

    # Remove anticipations
    srt_clean = srt_valid[
        srt_valid["Adjusted_RT"] >= anticipation_threshold
    ].copy()

    srt_clean_trials = len(srt_clean)

    # --------------------------------
    # Summary statistics
    # --------------------------------

    if srt_clean_trials > 0:

        mean_adjusted_rt = srt_clean["Adjusted_RT"].mean()

        median_adjusted_rt = srt_clean["Adjusted_RT"].median()

        sd_adjusted_rt = srt_clean["Adjusted_RT"].std()

        cv_adjusted_rt = (
            sd_adjusted_rt / mean_adjusted_rt
            if mean_adjusted_rt > 0
            else np.nan
        )

        min_adjusted_rt = srt_clean["Adjusted_RT"].min()

        max_adjusted_rt = srt_clean["Adjusted_RT"].max()

    else:

        mean_adjusted_rt = np.nan
        median_adjusted_rt = np.nan
        sd_adjusted_rt = np.nan
        cv_adjusted_rt = np.nan
        min_adjusted_rt = np.nan
        max_adjusted_rt = np.nan

    # --------------------------------
    # Quality control
    # --------------------------------

    SRT_QC_OK = (
        srt_valid_trials >= min_valid_trials
        and n_anticipations <= max_anticipations
        and not np.isnan(mean_adjusted_rt)
        and min_mean_rt_sec <= mean_adjusted_rt <= max_mean_rt_sec
    )

    # --------------------------------
    # Save individual results
    # --------------------------------

    srt_results_df = pd.DataFrame({
        "Trials": [srt_trials],
        "Valid_Trials": [srt_valid_trials],
        "Clean_Trials": [srt_clean_trials],
        "Misses": [srt_misses],
        "Anticipations": [n_anticipations],

        "Mean_Adjusted_RT_ms": [
            mean_adjusted_rt * 1000
        ],

        "Median_Adjusted_RT_ms": [
            median_adjusted_rt * 1000
        ],

        "SD_Adjusted_RT_ms": [
            sd_adjusted_rt * 1000
        ],

        "CV_Adjusted_RT": [
            cv_adjusted_rt
        ],

        "Fastest_RT_ms": [
            min_adjusted_rt * 1000
        ],

        "Slowest_RT_ms": [
            max_adjusted_rt * 1000
        ],

        "SRT_QC_OK": [
            SRT_QC_OK
        ]
    })

    srt_results_df.to_csv(
        os.path.join(
            participant_folder,
            "SRT_Results.csv"
        ),
        index=False
    )

    # --------------------------------
    # Print summary
    # --------------------------------

    print("\n===================================")
    print(" SRT Analysis")
    print("===================================")

    print(f"Trials            : {srt_trials}")
    print(f"Valid RTs         : {srt_valid_trials}")
    print(f"Clean RTs         : {srt_clean_trials}")
    print(f"Misses            : {srt_misses}")
    print(f"Anticipations     : {n_anticipations}")

    print(
        f"Mean Adjusted RT   : "
        f"{mean_adjusted_rt * 1000:.1f} ms"
    )

    print(
        f"Median Adjusted RT : "
        f"{median_adjusted_rt * 1000:.1f} ms"
    )

    print(
        f"SD Adjusted RT     : "
        f"{sd_adjusted_rt * 1000:.1f} ms"
    )

    print(f"CV                 : {cv_adjusted_rt:.3f}")

    print(
        f"Fastest RT         : "
        f"{min_adjusted_rt * 1000:.1f} ms"
    )

    print(
        f"Slowest RT         : "
        f"{max_adjusted_rt * 1000:.1f} ms"
    )

    if not SRT_QC_OK:
        print(
            "WARNING: SRT failed quality control. "
            "Inspect this participant."
        )

    # --------------------------------
    # Histogram
    # --------------------------------

    if srt_clean_trials > 0:

        plt.figure(figsize=(8, 5))

        plt.hist(
            srt_clean["Adjusted_RT"] * 1000,
            bins=25,
            edgecolor="black"
        )

        plt.xlabel("Adjusted Reaction Time (ms)")
        plt.ylabel("Frequency")

        plt.title(
            "Simple Reaction Time Distribution"
        )

        plt.grid(True)
        plt.tight_layout()

        plt.savefig(
            os.path.join(
                participant_folder,
                "SRT_Histogram.png"
            ),
            dpi=300
        )

        plt.close()

    # --------------------------------
    # Return results
    # --------------------------------

    return {
        "SRT_Trials": srt_trials,
        "SRT_Valid_Trials": srt_valid_trials,
        "SRT_Clean_Trials": srt_clean_trials,
        "SRT_Misses": srt_misses,
        "SRT_Anticipations": n_anticipations,

        "Mean_Adjusted_RT_ms":
            mean_adjusted_rt * 1000,

        "Median_Adjusted_RT_ms":
            median_adjusted_rt * 1000,

        "SD_Adjusted_RT_ms":
            sd_adjusted_rt * 1000,

        "CV_Adjusted_RT":
            cv_adjusted_rt,

        "Fastest_RT_ms":
            min_adjusted_rt * 1000,

        "Slowest_RT_ms":
            max_adjusted_rt * 1000,

        "SRT_QC_OK":
            SRT_QC_OK
    }