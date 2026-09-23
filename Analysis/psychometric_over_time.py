import os
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.optimize import curve_fit
from scipy.special import expit

from tkinter import Tk
from tkinter.filedialog import (
    askopenfilenames,
    askdirectory
)


# ============================================================
# SETTINGS
# ============================================================

N_BINS = 4

# Catch trials are excluded from the psychometric fits.
CATCH_SOA_MS = 1000

# Fit limits
MAX_SIGMA_MS = 1000
MAX_TOJ_SLOPE_MS = 1000

# Dense x-axis for smooth fitted curves
FIT_X = np.linspace(
    -350,
    350,
    1000
)


# ============================================================
# PSYCHOMETRIC FUNCTIONS
# ============================================================

def gaussian(
    x,
    amplitude,
    mu,
    sigma
):
    """
    Gaussian used for SJ.

    amplitude:
        peak probability of responding simultaneous

    mu:
        PSS

    sigma:
        width of the simultaneity function
    """

    return (
        amplitude
        * np.exp(
            -0.5
            * (
                (x - mu)
                / sigma
            ) ** 2
        )
    )


def logistic(
    x,
    x0,
    slope
):
    """
    Logistic psychometric function used for TOJ.

    x0:
        PSS / midpoint

    slope:
        transition width
    """

    return expit(
        (x - x0)
        / slope
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_numeric(
    series
):
    return pd.to_numeric(
        series,
        errors="coerce"
    )


def get_participant_id(
    df,
    filename
):
    """
    Get participant ID from the CSV when available.
    """

    if (
        "Participant_ID"
        in df.columns
        and not df.empty
    ):

        return str(
            df[
                "Participant_ID"
            ].iloc[0]
        )

    return os.path.splitext(
        os.path.basename(
            filename
        )
    )[0]


def calculate_r2(
    observed,
    predicted
):
    """
    Calculate R-squared.
    """

    observed = np.asarray(
        observed,
        dtype=float
    )

    predicted = np.asarray(
        predicted,
        dtype=float
    )

    ss_res = np.sum(
        (
            observed
            - predicted
        ) ** 2
    )

    ss_tot = np.sum(
        (
            observed
            - np.mean(
                observed
            )
        ) ** 2
    )

    if ss_tot == 0:
        return np.nan

    return (
        1
        - (
            ss_res
            / ss_tot
        )
    )


# ============================================================
# SPLIT TASK INTO FOUR CHRONOLOGICAL QUARTERS
# ============================================================

def split_into_time_bins(
    task_df,
    n_bins=N_BINS
):
    """
    Split a task into approximately equal chronological bins.

    Example with 400 trials:

        Bin 1 = 1-100
        Bin 2 = 101-200
        Bin 3 = 201-300
        Bin 4 = 301-400

    If trial count is not divisible by four, bins differ
    by at most one trial.
    """

    task_df = (
        task_df
        .copy()
        .reset_index(
            drop=True
        )
    )

    task_df[
        "Analysis_Trial"
    ] = (
        np.arange(
            len(task_df)
        )
        + 1
    )

    # np.array_split preserves chronological order
    split_indices = np.array_split(
        np.arange(
            len(task_df)
        ),
        n_bins
    )

    task_df[
        "Time_Bin"
    ] = np.nan

    for bin_number, indices in enumerate(
        split_indices,
        start=1
    ):

        task_df.loc[
            indices,
            "Time_Bin"
        ] = bin_number

    task_df[
        "Time_Bin"
    ] = (
        task_df[
            "Time_Bin"
        ]
        .astype(int)
    )

    return task_df


def get_bin_trial_range(
    bin_df
):
    """
    Return a readable trial range.
    """

    if bin_df.empty:
        return "No trials"

    first_trial = int(
        bin_df[
            "Analysis_Trial"
        ].min()
    )

    last_trial = int(
        bin_df[
            "Analysis_Trial"
        ].max()
    )

    return (
        f"{first_trial}-{last_trial}"
    )


# ============================================================
# SJ ANALYSIS
# ============================================================

def analyze_sj_bin(
    bin_df
):
    """
    Fit one SJ psychometric curve to one chronological quarter.

    Assumes:
        Response 1 = simultaneous
        Response 2 = not simultaneous
    """

    data = bin_df.copy()

    data[
        "SOA"
    ] = safe_numeric(
        data[
            "SOA"
        ]
    )

    data[
        "Response"
    ] = safe_numeric(
        data[
            "Response"
        ]
    )

    # Remove missing responses/SOAs
    data = data.dropna(
        subset=[
            "SOA",
            "Response"
        ]
    )

    if data.empty:

        return None

    # ----------------------------------------
    # Convert response to simultaneous = 1/0
    # ----------------------------------------

    data[
        "Simultaneous"
    ] = (
        data[
            "Response"
        ]
        == 1
    ).astype(float)

    # ----------------------------------------
    # Observed proportion at each SOA
    # ----------------------------------------

    observed = (
        data
        .groupby(
            "SOA",
            as_index=False
        )
        .agg(
            Proportion_Simultaneous=(
                "Simultaneous",
                "mean"
            ),

            N=(
                "Simultaneous",
                "count"
            )
        )
        .sort_values(
            "SOA"
        )
    )

    if len(
        observed
    ) < 3:

        return None

    x = (
        observed[
            "SOA"
        ]
        .to_numpy(
            dtype=float
        )
    )

    y = (
        observed[
            "Proportion_Simultaneous"
        ]
        .to_numpy(
            dtype=float
        )
    )

    # ----------------------------------------
    # Initial values
    # ----------------------------------------

    amplitude_guess = min(
        1.0,
        max(
            0.1,
            np.max(
                y
            )
        )
    )

    mu_guess = x[
        np.argmax(
            y
        )
    ]

    sigma_guess = 150.0

    # ----------------------------------------
    # Fit Gaussian
    # ----------------------------------------

    try:

        params, _ = curve_fit(
            gaussian,
            x,
            y,

            p0=[
                amplitude_guess,
                mu_guess,
                sigma_guess
            ],

            bounds=(
                [
                    0.0,
                    -500.0,
                    1.0
                ],

                [
                    1.0,
                    500.0,
                    MAX_SIGMA_MS
                ]
            ),

            maxfev=20000
        )

        amplitude, pss, sigma = (
            params
        )

        predicted = gaussian(
            x,
            *params
        )

        r2 = calculate_r2(
            y,
            predicted
        )

        # Full width at half maximum
        tbw = (
            2.35482
            * sigma
        )

        fit_y = gaussian(
            FIT_X,
            *params
        )

        return {
            "observed":
                observed,

            "fit_x":
                FIT_X.copy(),

            "fit_y":
                fit_y,

            "Amplitude":
                amplitude,

            "PSS_ms":
                pss,

            "Sigma_ms":
                sigma,

            "TBW_ms":
                tbw,

            "R2":
                r2,

            "N_Trials":
                len(data)
        }

    except (
        RuntimeError,
        ValueError
    ) as error:

        warnings.warn(
            f"SJ fit failed: {error}"
        )

        return {
            "observed":
                observed,

            "fit_x":
                None,

            "fit_y":
                None,

            "Amplitude":
                np.nan,

            "PSS_ms":
                np.nan,

            "Sigma_ms":
                np.nan,

            "TBW_ms":
                np.nan,

            "R2":
                np.nan,

            "N_Trials":
                len(data)
        }


# ============================================================
# TOJ ANALYSIS
# ============================================================

def analyze_toj_bin(
    bin_df
):
    """
    Fit one TOJ psychometric curve to one chronological quarter.

    Assumes:
        Response 1 = Audio first
        Response 2 = Visual first

    We model probability of responding Visual First.
    """

    data = bin_df.copy()

    data[
        "SOA"
    ] = safe_numeric(
        data[
            "SOA"
        ]
    )

    data[
        "Response"
    ] = safe_numeric(
        data[
            "Response"
        ]
    )

    data = data.dropna(
        subset=[
            "SOA",
            "Response"
        ]
    )

    if data.empty:

        return None

    # ----------------------------------------
    # Visual-first response = 1
    # Audio-first response = 0
    # ----------------------------------------

    data[
        "Visual_First"
    ] = (
        data[
            "Response"
        ]
        == 2
    ).astype(float)

    # ----------------------------------------
    # Observed proportion at each SOA
    # ----------------------------------------

    observed = (
        data
        .groupby(
            "SOA",
            as_index=False
        )
        .agg(
            Proportion_Visual_First=(
                "Visual_First",
                "mean"
            ),

            N=(
                "Visual_First",
                "count"
            )
        )
        .sort_values(
            "SOA"
        )
    )

    if len(
        observed
    ) < 3:

        return None

    x = (
        observed[
            "SOA"
        ]
        .to_numpy(
            dtype=float
        )
    )

    y = (
        observed[
            "Proportion_Visual_First"
        ]
        .to_numpy(
            dtype=float
        )
    )

    # ----------------------------------------
    # Initial guesses
    # ----------------------------------------

    x0_guess = 0.0
    slope_guess = 100.0

    # ----------------------------------------
    # Fit logistic
    # ----------------------------------------

    try:

        params, _ = curve_fit(
            logistic,
            x,
            y,

            p0=[
                x0_guess,
                slope_guess
            ],

            bounds=(
                [
                    -500.0,
                    1.0
                ],

                [
                    500.0,
                    MAX_TOJ_SLOPE_MS
                ]
            ),

            maxfev=20000
        )

        pss, slope = (
            params
        )

        predicted = logistic(
            x,
            *params
        )

        r2 = calculate_r2(
            y,
            predicted
        )

        # For logistic:
        # JND = half distance between 25% and 75%
        jnd = (
            np.log(
                3
            )
            * slope
        )

        fit_y = logistic(
            FIT_X,
            *params
        )

        return {
            "observed":
                observed,

            "fit_x":
                FIT_X.copy(),

            "fit_y":
                fit_y,

            "PSS_ms":
                pss,

            "Slope":
                slope,

            "JND_ms":
                jnd,

            "R2":
                r2,

            "N_Trials":
                len(data)
        }

    except (
        RuntimeError,
        ValueError
    ) as error:

        warnings.warn(
            f"TOJ fit failed: {error}"
        )

        return {
            "observed":
                observed,

            "fit_x":
                None,

            "fit_y":
                None,

            "PSS_ms":
                np.nan,

            "Slope":
                np.nan,

            "JND_ms":
                np.nan,

            "R2":
                np.nan,

            "N_Trials":
                len(data)
        }


# ============================================================
# SJ FIGURE
# ============================================================

def plot_sj_four_bins(
    participant_id,
    bin_results,
    output_path
):
    """
    Plot all four SJ psychometric curves on one graph.
    """

    plt.figure(
        figsize=(
            10,
            7
        )
    )

    for result in bin_results:

        if result[
            "result"
        ] is None:

            continue

        fit_result = (
            result[
                "result"
            ]
        )

        label = (
            f"Bin {result['bin']} "
            f"(Trials {result['range']})"
        )

        # ----------------------------------------
        # Raw observed probabilities
        # ----------------------------------------

        observed = (
            fit_result[
                "observed"
            ]
        )

        plt.scatter(
            observed[
                "SOA"
            ],
            observed[
                "Proportion_Simultaneous"
            ],
            alpha=0.45,
            s=35
        )

        # ----------------------------------------
        # Fitted curve
        # ----------------------------------------

        if (
            fit_result[
                "fit_x"
            ]
            is not None
        ):

            plt.plot(
                fit_result[
                    "fit_x"
                ],
                fit_result[
                    "fit_y"
                ],
                linewidth=2.5,
                label=label
            )

    plt.xlabel(
        "Stimulus Onset Asynchrony (ms)"
    )

    plt.ylabel(
        'Proportion "Simultaneous"'
    )

    plt.title(
        f"Participant {participant_id} - "
        f"SJ Psychometric Function Across Time"
    )

    plt.ylim(
        -0.05,
        1.05
    )

    plt.xlim(
        -350,
        350
    )

    plt.axvline(
        0,
        linewidth=1,
        alpha=0.4
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300
    )

    plt.close()


# ============================================================
# TOJ FIGURE
# ============================================================

def plot_toj_four_bins(
    participant_id,
    bin_results,
    output_path
):
    """
    Plot all four TOJ psychometric curves on one graph.
    """

    plt.figure(
        figsize=(
            10,
            7
        )
    )

    for result in bin_results:

        if result[
            "result"
        ] is None:

            continue

        fit_result = (
            result[
                "result"
            ]
        )

        label = (
            f"Bin {result['bin']} "
            f"(Trials {result['range']})"
        )

        # ----------------------------------------
        # Raw observed probabilities
        # ----------------------------------------

        observed = (
            fit_result[
                "observed"
            ]
        )

        plt.scatter(
            observed[
                "SOA"
            ],
            observed[
                "Proportion_Visual_First"
            ],
            alpha=0.45,
            s=35
        )

        # ----------------------------------------
        # Fitted curve
        # ----------------------------------------

        if (
            fit_result[
                "fit_x"
            ]
            is not None
        ):

            plt.plot(
                fit_result[
                    "fit_x"
                ],
                fit_result[
                    "fit_y"
                ],
                linewidth=2.5,
                label=label
            )

    plt.xlabel(
        "Stimulus Onset Asynchrony (ms)"
    )

    plt.ylabel(
        'Proportion "Visual First"'
    )

    plt.title(
        f"Participant {participant_id} - "
        f"TOJ Psychometric Function Across Time"
    )

    plt.ylim(
        -0.05,
        1.05
    )

    plt.xlim(
        -350,
        350
    )

    plt.axvline(
        0,
        linewidth=1,
        alpha=0.4
    )

    plt.axhline(
        0.5,
        linewidth=1,
        alpha=0.4
    )

    plt.grid(
        alpha=0.25
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300
    )

    plt.close()


# ============================================================
# ANALYZE ONE PARTICIPANT
# ============================================================

def analyze_participant(
    file,
    output_folder
):

    filename = os.path.basename(
        file
    )

    print(
        "\n======================================"
    )

    print(
        f"Analyzing: {filename}"
    )

    df = pd.read_csv(
        file
    )

    if (
        "Experiment"
        not in df.columns
    ):

        print(
            "Experiment column not found. "
            "Skipping participant."
        )

        return []

    participant_id = (
        get_participant_id(
            df,
            file
        )
    )

    participant_folder = os.path.join(
        output_folder,
        f"Participant_{participant_id}"
    )

    os.makedirs(
        participant_folder,
        exist_ok=True
    )

    all_summary_rows = []

    # ========================================================
    # SJ
    # ========================================================

    sj = df[
        df[
            "Experiment"
        ]
        .astype(str)
        .str.lower()
        == "sj"
    ].copy()

    if not sj.empty:

        sj[
            "SOA"
        ] = safe_numeric(
            sj[
                "SOA"
            ]
        )

        # ----------------------------------------
        # Remove catch trials BEFORE splitting.
        #
        # This means the four quarters represent
        # the actual psychometric-analysis trials.
        # ----------------------------------------

        sj_fit_trials = sj[
            sj[
                "SOA"
            ].abs()
            != CATCH_SOA_MS
        ].copy()

        sj_fit_trials = (
            sj_fit_trials
            .reset_index(
                drop=True
            )
        )

        sj_fit_trials = (
            split_into_time_bins(
                sj_fit_trials
            )
        )

        print(
            f"SJ analyzable trials: "
            f"{len(sj_fit_trials)}"
        )

        sj_bin_results = []

        for bin_number in range(
            1,
            N_BINS + 1
        ):

            bin_df = sj_fit_trials[
                sj_fit_trials[
                    "Time_Bin"
                ]
                == bin_number
            ].copy()

            trial_range = (
                get_bin_trial_range(
                    bin_df
                )
            )

            result = analyze_sj_bin(
                bin_df
            )

            sj_bin_results.append({
                "bin":
                    bin_number,

                "range":
                    trial_range,

                "result":
                    result
            })

            if result is not None:

                all_summary_rows.append({

                    "Participant_ID":
                        participant_id,

                    "Task":
                        "SJ",

                    "Time_Bin":
                        bin_number,

                    "Trial_Range":
                        trial_range,

                    "N_Trials":
                        result[
                            "N_Trials"
                        ],

                    "PSS_ms":
                        result[
                            "PSS_ms"
                        ],

                    "Sigma_ms":
                        result[
                            "Sigma_ms"
                        ],

                    "TBW_ms":
                        result[
                            "TBW_ms"
                        ],

                    "Slope":
                        np.nan,

                    "JND_ms":
                        np.nan,

                    "R2":
                        result[
                            "R2"
                        ]
                })

                print(
                    f"SJ Bin {bin_number} "
                    f"({trial_range}): "
                    f"PSS={result['PSS_ms']:.1f} ms, "
                    f"Sigma={result['Sigma_ms']:.1f} ms, "
                    f"TBW={result['TBW_ms']:.1f} ms, "
                    f"R²={result['R2']:.3f}"
                )

        plot_sj_four_bins(
            participant_id,
            sj_bin_results,
            os.path.join(
                participant_folder,
                "SJ_Psychometric_Over_Time.png"
            )
        )

    else:

        print(
            "No SJ trials found."
        )

    # ========================================================
    # TOJ
    # ========================================================

    toj = df[
        df[
            "Experiment"
        ]
        .astype(str)
        .str.lower()
        == "toj"
    ].copy()

    if not toj.empty:

        toj[
            "SOA"
        ] = safe_numeric(
            toj[
                "SOA"
            ]
        )

        # Remove +/-1000-ms catch trials
        toj_fit_trials = toj[
            toj[
                "SOA"
            ].abs()
            != CATCH_SOA_MS
        ].copy()

        toj_fit_trials = (
            toj_fit_trials
            .reset_index(
                drop=True
            )
        )

        toj_fit_trials = (
            split_into_time_bins(
                toj_fit_trials
            )
        )

        print(
            f"TOJ analyzable trials: "
            f"{len(toj_fit_trials)}"
        )

        toj_bin_results = []

        for bin_number in range(
            1,
            N_BINS + 1
        ):

            bin_df = toj_fit_trials[
                toj_fit_trials[
                    "Time_Bin"
                ]
                == bin_number
            ].copy()

            trial_range = (
                get_bin_trial_range(
                    bin_df
                )
            )

            result = analyze_toj_bin(
                bin_df
            )

            toj_bin_results.append({
                "bin":
                    bin_number,

                "range":
                    trial_range,

                "result":
                    result
            })

            if result is not None:

                all_summary_rows.append({

                    "Participant_ID":
                        participant_id,

                    "Task":
                        "TOJ",

                    "Time_Bin":
                        bin_number,

                    "Trial_Range":
                        trial_range,

                    "N_Trials":
                        result[
                            "N_Trials"
                        ],

                    "PSS_ms":
                        result[
                            "PSS_ms"
                        ],

                    "Sigma_ms":
                        np.nan,

                    "TBW_ms":
                        np.nan,

                    "Slope":
                        result[
                            "Slope"
                        ],

                    "JND_ms":
                        result[
                            "JND_ms"
                        ],

                    "R2":
                        result[
                            "R2"
                        ]
                })

                print(
                    f"TOJ Bin {bin_number} "
                    f"({trial_range}): "
                    f"PSS={result['PSS_ms']:.1f} ms, "
                    f"Slope={result['Slope']:.1f}, "
                    f"JND={result['JND_ms']:.1f} ms, "
                    f"R²={result['R2']:.3f}"
                )

        plot_toj_four_bins(
            participant_id,
            toj_bin_results,
            os.path.join(
                participant_folder,
                "TOJ_Psychometric_Over_Time.png"
            )
        )

    else:

        print(
            "No TOJ trials found."
        )

    return all_summary_rows


# ============================================================
# MULTIPLE PARTICIPANTS
# ============================================================

def analyze_files(
    selected_files,
    output_folder
):

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    all_results = []

    for file in selected_files:

        participant_results = (
            analyze_participant(
                file,
                output_folder
            )
        )

        all_results.extend(
            participant_results
        )

    # ========================================================
    # SAVE MASTER RESULTS
    # ========================================================

    if all_results:

        master_df = pd.DataFrame(
            all_results
        )

        master_path = os.path.join(
            output_folder,
            "Psychometric_Over_Time_Master.csv"
        )

        master_df.to_csv(
            master_path,
            index=False
        )

        print(
            "\n======================================"
        )

        print(
            "Psychometric-over-time analysis complete."
        )

        print(
            f"Master results:\n{master_path}"
        )

        print(
            "======================================"
        )

        return master_df

    print(
        "No SJ or TOJ data were available."
    )

    return pd.DataFrame()

# ============================================================
# RUN SCRIPT
# ============================================================

if __name__ == "__main__":

    root = Tk()
    root.withdraw()

    # ========================================================
    # SELECT MULTIPLE PARTICIPANT FILES
    # ========================================================

    selected_files = askopenfilenames(
        title=(
            "Select ALL Participant CSV Files "
            "for Psychometric Over-Time Analysis"
        ),
        initialdir="../Data",
        filetypes=[
            (
                "CSV Files",
                "*.csv"
            )
        ]
    )

    # Convert tkinter tuple to normal list
    selected_files = list(
        selected_files
    )

    # ========================================================
    # MAKE SURE FILES WERE SELECTED
    # ========================================================

    if not selected_files:

        root.destroy()

        print(
            "No participant files selected."
        )

        raise SystemExit

    # ========================================================
    # SHOW SELECTED PARTICIPANTS
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        f"{len(selected_files)} participant file(s) selected:"
    )

    print(
        "======================================"
    )

    for file_number, file in enumerate(
        selected_files,
        start=1
    ):

        print(
            f"{file_number}. "
            f"{os.path.basename(file)}"
        )

    # ========================================================
    # SELECT OUTPUT FOLDER
    # ========================================================

    base_output_folder = askdirectory(
        title=(
            "Select Folder for "
            "Psychometric Over-Time Results"
        )
    )

    root.destroy()

    if not base_output_folder:

        print(
            "No output folder selected."
        )

        raise SystemExit

    # ========================================================
    # CREATE ANALYSIS FOLDER
    # ========================================================

    output_folder = os.path.join(
        base_output_folder,
        "Psychometric_Over_Time"
    )

    os.makedirs(
        output_folder,
        exist_ok=True
    )

    # ========================================================
    # RUN ALL SELECTED PARTICIPANTS
    # ========================================================

    master_results = analyze_files(
        selected_files,
        output_folder
    )

    # ========================================================
    # FINISHED
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        "ALL PARTICIPANTS COMPLETE"
    )

    print(
        "======================================"
    )

    print(
        f"Participants selected: "
        f"{len(selected_files)}"
    )

    print(
        f"\nResults saved to:\n"
        f"{output_folder}"
    )
