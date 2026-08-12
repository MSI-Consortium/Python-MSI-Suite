import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

#Define Logistic Function - TOJ
def logistic(x, PSS, slope):
    """
    Logistic psychometric function for Temporal Order Judgment

    PSS   = Point of Subjective Simultaneity
    slope = Controls steepness of the curve
    """

    return 1 / (1 + np.exp(-(x - PSS) / slope))

def analyze_toj(
    toj,
    participant_folder,
    min_r2=0.80,
    max_slope_ms=500,
    min_response_proportion=0.10,
    max_response_proportion=0.90
):
    """
    Analyze Temporal Order Judgment data for one participant.

    Returns a dictionary containing TOJ results and QC measures.
    """


    # Catch-trial QC: |SOA| == 1000 ms.
    # Negative SOA = audio first (correct response 1); positive SOA = visual first (correct response 2).
    catch_mask = toj["SOA"].abs() == 1000
    toj_catch = toj.loc[catch_mask].copy()
    toj_catch_trials = len(toj_catch)
    expected = np.where(toj_catch["SOA"] < 0, 1, 2)
    toj_catch_correct = int((toj_catch["Response"].to_numpy() == expected).sum())
    TOJ_Catch_OK = toj_catch_trials == 10 and toj_catch_correct >= 8

    # Exclude catch trials from the psychometric fit and ordinary response-bias QC.
    toj = toj.loc[~catch_mask].copy()

    # Convert responses to binary:
    # 1 = Visual First
    # 0 = Audio First
    toj = toj.copy()
    toj["Visual_First"] = (toj["Response"] == 2).astype(int)

    # Trial counts
    toj_trials = len(toj)
    toj_valid_trials = toj["Response"].notna().sum()

    # Response counts
    response_counts = toj["Response"].value_counts()

    toj_audio_first = response_counts.get(1, 0)
    toj_visual_first = response_counts.get(2, 0)

    # Response proportions
    audio_first_proportion = toj_audio_first / toj_trials
    visual_first_proportion = toj_visual_first / toj_trials

    # Response quality checks
    TOJ_Response_Range_OK = (
            toj_audio_first > 0
            and toj_visual_first > 0
    )

    TOJ_Response_Bias_OK = (
            min_response_proportion
            <= visual_first_proportion
            <= max_response_proportion
    )

    # Summary by SOA
    toj_summary = (
        toj.groupby("SOA")["Visual_First"]
        .agg(
            P_Visual_First="mean",
            Trials="count"
        )
        .reset_index()
    )

    x = toj_summary["SOA"].values
    y = toj_summary["P_Visual_First"].values

    initial_guess = [
        0,      # PSS
        50      # slope
    ]

    # Logistic fit
    try:
        params, covariance = curve_fit(
            logistic,
            x,
            y,
            p0=initial_guess
        )

        PSS, slope = params

        # Predicted values
        y_fit = logistic(x, *params)

        # Smooth curve for plotting
        x_smooth = np.linspace(
            x.min(),
            x.max(),
            500
        )

        y_smooth = logistic(
            x_smooth,
            *params
        )

        # R-squared
        ss_res = np.sum((y - y_fit) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r_squared = 1 - (ss_res / ss_tot)

        # JND
        JND = np.log(3) * slope

        # Fit QC
        TOJ_Fit_OK = (
            r_squared >= min_r2
            and slope > 0
            and slope < max_slope_ms
        )

    except RuntimeError:

        PSS = np.nan
        slope = np.nan
        JND = np.nan
        r_squared = np.nan
        TOJ_Fit_OK = False

        x_smooth = None
        y_smooth = None

    # Save individual TOJ results
    # Create dictionary of trial counts for each SOA
    soa_trial_counts = {
        f"Trials_SOA_{int(row['SOA'])}ms": int(row["Trials"])
        for _, row in toj_summary.iterrows()
    }

    # Save individual TOJ results
    toj_results = pd.DataFrame({
        "PSS_ms": [PSS],
        "Slope": [slope],
        "JND_ms": [JND],
        "R2": [r_squared],
        "TOJ_Fit_OK": [TOJ_Fit_OK],
        "TOJ_Catch_Trials": [toj_catch_trials],
        "TOJ_Catch_Correct": [toj_catch_correct],
        "TOJ_Catch_OK": [TOJ_Catch_OK],
        **soa_trial_counts
    })

    toj_results.to_csv(
        os.path.join(participant_folder, "TOJ_Results.csv"),
        index=False
    )

    # --------------------------------
    # Raw TOJ Plot
    # --------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        x,
        y,
        "o-",
        linewidth=2,
        label="Observed Data"
    )

    plt.xlabel("SOA (ms)")
    plt.ylabel("Probability Visual First")
    plt.title("Temporal Order Judgment - Raw Data")

    plt.ylim(0, 1)

    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            participant_folder,
            "TOJ_Raw.png"
        ),
        dpi=300
    )

    plt.close()

    # --------------------------------
    # Fitted TOJ Plot
    # --------------------------------

    plt.figure(figsize=(8, 5))

    # Observed data
    plt.plot(
        x,
        y,
        "o",
        label="Observed Data"
    )

    # Logistic fit
    if x_smooth is not None:
        plt.plot(
            x_smooth,
            y_smooth,
            linewidth=2,
            label="Logistic Fit"
        )

    plt.xlabel("SOA (ms)")
    plt.ylabel("Probability Visual First")
    plt.title("Temporal Order Judgment - Logistic Fit")

    plt.ylim(0, 1)

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            participant_folder,
            "TOJ_Fitted.png"
        ),
        dpi=300
    )

    plt.close()

    # Print summary
    print("\n===================================")
    print(" TOJ Psychometric Analysis")
    print("===================================")

    print(f"PSS        : {PSS:.2f} ms")
    print(f"Slope      : {slope:.2f}")
    print(f"JND        : {JND:.2f} ms")
    print(f"R²         : {r_squared:.3f}")

    if not TOJ_Fit_OK:
        print("WARNING: TOJ fit is poor. Inspect this participant.")

    # Return results to Main_Analysis
    return {
        "TOJ_Trials": toj_trials,
        "TOJ_Catch_Trials": toj_catch_trials,
        "TOJ_Catch_Correct": toj_catch_correct,
        "TOJ_Catch_OK": TOJ_Catch_OK,
        "TOJ_Valid_Trials": toj_valid_trials,

        "TOJ_Audio_First": toj_audio_first,
        "TOJ_Visual_First": toj_visual_first,

        "TOJ_Audio_First_Proportion": audio_first_proportion,
        "TOJ_Visual_First_Proportion": visual_first_proportion,

        "TOJ_Response_Range_OK": TOJ_Response_Range_OK,
        "TOJ_Response_Bias_OK": TOJ_Response_Bias_OK,

        "TOJ_PSS_ms": PSS,
        "TOJ_Slope": slope,
        "TOJ_JND_ms": JND,
        "TOJ_R2": r_squared,
        "TOJ_Fit_OK": TOJ_Fit_OK
    }