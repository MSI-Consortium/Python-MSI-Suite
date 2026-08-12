import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


#Define Gaussian Function - SJ
def gaussian(x, A, mu, sigma):
    """
    Gaussian function for Simultaneity Judgment
    A     = Peak probability
    mu    = Point of Subjective Simultaneity (PSS)
    sigma = Width of the curve
    """
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def analyze_sj(
    sj,
    participant_folder,
    min_r2=0.80,
    max_sigma_ms=500,
    min_response_proportion=0.10,
    max_response_proportion=0.90
):
    """
    Analyze Simultaneity Judgment data for one participant.

    Returns a dictionary containing SJ results and QC measures.
    """

    # Catch-trial QC: |SOA| == 1000 ms. Correct SJ response is "Different Time" (2).
    catch_mask = sj["SOA"].abs() == 1000
    sj_catch = sj.loc[catch_mask].copy()
    sj_catch_trials = len(sj_catch)
    sj_catch_correct = int((sj_catch["Response"] == 2).sum())
    SJ_Catch_OK = sj_catch_trials == 10 and sj_catch_correct >= 8

    # Exclude catch trials from the psychometric fit and ordinary response-bias QC.
    sj = sj.loc[~catch_mask].copy()

    # Convert response to binary:
    # 1 = Simultaneous
    # 0 = Not Simultaneous
    sj = sj.copy()
    sj["Simultaneous"] = (sj["Response"] == 1).astype(int)

    # Trial counts
    sj_trials = len(sj)
    sj_valid_trials = sj["Response"].notna().sum()

    # Response counts
    response_counts = sj["Response"].value_counts()

    sj_simultaneous = response_counts.get(1, 0)
    sj_not_simultaneous = response_counts.get(2, 0)

    # Response proportions
    simultaneous_proportion = sj_simultaneous / sj_trials
    not_simultaneous_proportion = sj_not_simultaneous / sj_trials

    # Response quality checks
    SJ_Response_Range_OK = (
            sj_simultaneous > 0
            and sj_not_simultaneous > 0
    )

    SJ_Response_Bias_OK = (
            min_response_proportion
            <= simultaneous_proportion
            <= max_response_proportion
    )

    # Summary by SOA
    sj_summary = (
        sj.groupby("SOA")["Simultaneous"]
        .agg(
            P_Simultaneous="mean",
            Trials="count"
        )
        .reset_index()
    )

    # Values used for Gaussian fitting
    x = sj_summary["SOA"].values
    y = sj_summary["P_Simultaneous"].values

    initial_guess = [
        max(y),
        x[np.argmax(y)],
        150
    ]

    # Gaussian fit
    try:
        params, covariance = curve_fit(
            gaussian,
            x,
            y,
            p0=initial_guess,
            bounds=(
                [
                    0.0,  # A minimum
                    x.min(),  # PSS minimum
                    0.001  # sigma minimum
                ],
                [
                    1.0,  # A maximum
                    x.max(),  # PSS maximum
                    np.inf  # sigma maximum
                ]
            ),
            maxfev=10000
        )

        A, PSS, sigma = params

        # Temporal Binding Window
        TBW = 2.355 * sigma

        # Predicted values
        y_fit = gaussian(x, *params)

        # Smooth curve for plotting
        x_smooth = np.linspace(
            x.min(),
            x.max(),
            500
        )

        y_smooth = gaussian(
            x_smooth,
            *params
        )

        # R-squared
        ss_res = np.sum((y - y_fit) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r_squared = 1 - (ss_res / ss_tot)

        # Fit QC
        SJ_Fit_OK = (
            r_squared >= min_r2
            and sigma > 0
            and sigma < max_sigma_ms
        )

    except RuntimeError:

        A = np.nan
        PSS = np.nan
        sigma = np.nan
        TBW = np.nan
        r_squared = np.nan
        SJ_Fit_OK = False

        x_smooth = None
        y_smooth = None

    # Save individual SJ results
    # Create dictionary of trial counts for each SOA
    soa_trial_counts = {
        f"Trials_SOA_{int(row['SOA'])}ms": int(row["Trials"])
        for _, row in sj_summary.iterrows()
    }

    # Save individual SJ results
    sj_results = pd.DataFrame({
        "Peak_Probability": [A],
        "PSS_ms": [PSS],
        "Sigma_ms": [sigma],
        "TBW_ms": [TBW],
        "R2": [r_squared],
        "SJ_Fit_OK": [SJ_Fit_OK],
        "SJ_Catch_Trials": [sj_catch_trials],
        "SJ_Catch_Correct": [sj_catch_correct],
        "SJ_Catch_OK": [SJ_Catch_OK],
        **soa_trial_counts
    })

    sj_results.to_csv(
        os.path.join(participant_folder, "SJ_Results.csv"),
        index=False
    )

    # --------------------------------
    # Raw SJ Plot
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
    plt.ylabel("Probability Simultaneous")
    plt.title("Simultaneity Judgment - Raw Data")

    plt.ylim(0, 1.05)

    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            participant_folder,
            "SJ_Raw.png"
        ),
        dpi=300
    )

    plt.close()

    # --------------------------------
    # Fitted SJ Plot
    # --------------------------------

    plt.figure(figsize=(8, 5))

    # Observed data
    plt.plot(
        x,
        y,
        "o",
        label="Observed Data"
    )

    # Gaussian fit
    if x_smooth is not None:
        plt.plot(
            x_smooth,
            y_smooth,
            linewidth=2,
            label="Gaussian Fit"
        )

    plt.xlabel("SOA (ms)")
    plt.ylabel("Probability Simultaneous")
    plt.title("Simultaneity Judgment - Gaussian Fit")

    if y_smooth is not None:

        y_max = max(
            1.0,
            np.max(y),
            np.max(y_smooth)
        )

    else:

        y_max = max(
            1.0,
            np.max(y)
        )

    plt.ylim(
        -0.05,
        y_max + 0.05
    )

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            participant_folder,
            "SJ_Fitted.png"
        ),
        dpi=300
    )

    plt.close()

    # Print summary
    print("\n===================================")
    print(" SJ Psychometric Analysis")
    print("===================================")

    print(f"Peak Probability : {A * 100:.1f}%")
    print(f"PSS              : {PSS:.2f} ms")
    print(f"Sigma            : {sigma:.2f} ms")
    print(f"TBW (FWHM)       : {TBW:.2f} ms")
    print(f"R²               : {r_squared:.3f}")

    if not SJ_Fit_OK:
        print("WARNING: SJ fit is poor. Inspect this participant.")

    # Return everything Main_Analysis needs
    return {
        "SJ_Trials": sj_trials,
        "SJ_Catch_Trials": sj_catch_trials,
        "SJ_Catch_Correct": sj_catch_correct,
        "SJ_Catch_OK": SJ_Catch_OK,
        "SJ_Valid_Trials": sj_valid_trials,

        "SJ_Simultaneous": sj_simultaneous,
        "SJ_Not_Simultaneous": sj_not_simultaneous,

        "SJ_Simultaneous_Proportion": simultaneous_proportion,
        "SJ_Not_Simultaneous_Proportion": not_simultaneous_proportion,

        "SJ_Response_Range_OK": SJ_Response_Range_OK,
        "SJ_Response_Bias_OK": SJ_Response_Bias_OK,

        "SJ_PSS_ms": PSS,
        "SJ_Sigma_ms": sigma,
        "SJ_TBW_ms": TBW,
        "SJ_R2": r_squared,
        "SJ_Fit_OK": SJ_Fit_OK
    }