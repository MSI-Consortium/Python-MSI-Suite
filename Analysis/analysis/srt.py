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

    Provides:
    - Overall SRT statistics
    - SRT quality control
    - Auditory-only RT statistics
    - Visual-only RT statistics
    - Audiovisual RT statistics
    - Overall RT histogram
    - Trial-level modality plot with condition means

    Returns a dictionary containing all SRT results.
    """

    # ==================================================
    # COPY DATA
    # ==================================================

    srt = srt.copy()

    # ==================================================
    # TRIAL COUNTS
    # ==================================================

    srt_trials = len(srt)

    # Keep trials containing an Adjusted_RT
    srt_valid = srt.dropna(
        subset=[
            "Adjusted_RT"
        ]
    ).copy()

    srt_valid_trials = len(
        srt_valid
    )

    srt_misses = (
        srt_trials
        - srt_valid_trials
    )

    # ==================================================
    # ANTICIPATORY RESPONSES
    # ==================================================

    # Convert ms threshold from GUI into seconds
    # because Adjusted_RT is stored in seconds.
    anticipation_threshold = (
        min_rt_ms / 1000
    )

    anticipations = srt_valid[
        srt_valid["Adjusted_RT"]
        < anticipation_threshold
    ]

    n_anticipations = len(
        anticipations
    )

    # Remove anticipatory responses
    srt_clean = srt_valid[
        srt_valid["Adjusted_RT"]
        >= anticipation_threshold
    ].copy()

    srt_clean_trials = len(
        srt_clean
    )

    # ==================================================
    # OVERALL SRT SUMMARY STATISTICS
    # ==================================================

    if srt_clean_trials > 0:

        mean_adjusted_rt = (
            srt_clean[
                "Adjusted_RT"
            ].mean()
        )

        median_adjusted_rt = (
            srt_clean[
                "Adjusted_RT"
            ].median()
        )

        sd_adjusted_rt = (
            srt_clean[
                "Adjusted_RT"
            ].std()
        )

        cv_adjusted_rt = (
            sd_adjusted_rt
            / mean_adjusted_rt
            if mean_adjusted_rt > 0
            else np.nan
        )

        min_adjusted_rt = (
            srt_clean[
                "Adjusted_RT"
            ].min()
        )

        max_adjusted_rt = (
            srt_clean[
                "Adjusted_RT"
            ].max()
        )

    else:

        mean_adjusted_rt = np.nan
        median_adjusted_rt = np.nan
        sd_adjusted_rt = np.nan
        cv_adjusted_rt = np.nan
        min_adjusted_rt = np.nan
        max_adjusted_rt = np.nan

    # ==================================================
    # SRT BY STIMULUS MODALITY
    # ==================================================

    modality_results = {}

    modality_labels = {
        "audio": "Audio",
        "visual": "Visual",
        "audiovisual": "Audiovisual"
    }

    # Make Trial_Type consistent
    if "Trial_Type" in srt_clean.columns:

        srt_clean[
            "Trial_Type_Clean"
        ] = (
            srt_clean[
                "Trial_Type"
            ]
            .astype(str)
            .str.strip()
            .str.lower()
        )

    else:

        # This prevents the analysis from crashing
        # if an older dataset does not contain Trial_Type.
        srt_clean[
            "Trial_Type_Clean"
        ] = ""

    for trial_type, label in (
        modality_labels.items()
    ):

        modality_data = srt_clean[
            srt_clean[
                "Trial_Type_Clean"
            ]
            == trial_type
        ][
            "Adjusted_RT"
        ]

        n_trials = len(
            modality_data
        )

        if n_trials > 0:

            mean_rt = (
                modality_data.mean()
            )

            median_rt = (
                modality_data.median()
            )

            sd_rt = (
                modality_data.std()
            )

            min_rt = (
                modality_data.min()
            )

            max_rt = (
                modality_data.max()
            )

        else:

            mean_rt = np.nan
            median_rt = np.nan
            sd_rt = np.nan
            min_rt = np.nan
            max_rt = np.nan

        modality_results[
            f"{label}_N"
        ] = n_trials

        modality_results[
            f"{label}_Mean_RT_ms"
        ] = (
            mean_rt * 1000
        )

        modality_results[
            f"{label}_Median_RT_ms"
        ] = (
            median_rt * 1000
        )

        modality_results[
            f"{label}_SD_RT_ms"
        ] = (
            sd_rt * 1000
        )

        modality_results[
            f"{label}_Fastest_RT_ms"
        ] = (
            min_rt * 1000
        )

        modality_results[
            f"{label}_Slowest_RT_ms"
        ] = (
            max_rt * 1000
        )

    # ==================================================
    # QUALITY CONTROL
    # ==================================================

    SRT_QC_OK = (
        srt_valid_trials
        >= min_valid_trials

        and n_anticipations
        <= max_anticipations

        and not np.isnan(
            mean_adjusted_rt
        )

        and (
            min_mean_rt_sec
            <= mean_adjusted_rt
            <= max_mean_rt_sec
        )
    )

    # ==================================================
    # SAVE SRT RESULTS CSV
    # ==================================================

    srt_results_df = pd.DataFrame({

        # -------------------------
        # Overall SRT
        # -------------------------

        "Trials": [
            srt_trials
        ],

        "Valid_Trials": [
            srt_valid_trials
        ],

        "Clean_Trials": [
            srt_clean_trials
        ],

        "Misses": [
            srt_misses
        ],

        "Anticipations": [
            n_anticipations
        ],

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
        ],

        # -------------------------
        # Auditory Only
        # -------------------------

        "Audio_N": [
            modality_results[
                "Audio_N"
            ]
        ],

        "Audio_Mean_RT_ms": [
            modality_results[
                "Audio_Mean_RT_ms"
            ]
        ],

        "Audio_Median_RT_ms": [
            modality_results[
                "Audio_Median_RT_ms"
            ]
        ],

        "Audio_SD_RT_ms": [
            modality_results[
                "Audio_SD_RT_ms"
            ]
        ],

        "Audio_Fastest_RT_ms": [
            modality_results[
                "Audio_Fastest_RT_ms"
            ]
        ],

        "Audio_Slowest_RT_ms": [
            modality_results[
                "Audio_Slowest_RT_ms"
            ]
        ],

        # -------------------------
        # Visual Only
        # -------------------------

        "Visual_N": [
            modality_results[
                "Visual_N"
            ]
        ],

        "Visual_Mean_RT_ms": [
            modality_results[
                "Visual_Mean_RT_ms"
            ]
        ],

        "Visual_Median_RT_ms": [
            modality_results[
                "Visual_Median_RT_ms"
            ]
        ],

        "Visual_SD_RT_ms": [
            modality_results[
                "Visual_SD_RT_ms"
            ]
        ],

        "Visual_Fastest_RT_ms": [
            modality_results[
                "Visual_Fastest_RT_ms"
            ]
        ],

        "Visual_Slowest_RT_ms": [
            modality_results[
                "Visual_Slowest_RT_ms"
            ]
        ],

        # -------------------------
        # Audiovisual
        # -------------------------

        "Audiovisual_N": [
            modality_results[
                "Audiovisual_N"
            ]
        ],

        "Audiovisual_Mean_RT_ms": [
            modality_results[
                "Audiovisual_Mean_RT_ms"
            ]
        ],

        "Audiovisual_Median_RT_ms": [
            modality_results[
                "Audiovisual_Median_RT_ms"
            ]
        ],

        "Audiovisual_SD_RT_ms": [
            modality_results[
                "Audiovisual_SD_RT_ms"
            ]
        ],

        "Audiovisual_Fastest_RT_ms": [
            modality_results[
                "Audiovisual_Fastest_RT_ms"
            ]
        ],

        "Audiovisual_Slowest_RT_ms": [
            modality_results[
                "Audiovisual_Slowest_RT_ms"
            ]
        ]
    })

    srt_results_df.to_csv(
        os.path.join(
            participant_folder,
            "SRT_Results.csv"
        ),
        index=False
    )

    # ==================================================
    # PRINT OVERALL SUMMARY
    # ==================================================

    print(
        "\n==================================="
    )

    print(
        " SRT Analysis"
    )

    print(
        "==================================="
    )

    print(
        f"Trials            : "
        f"{srt_trials}"
    )

    print(
        f"Valid RTs         : "
        f"{srt_valid_trials}"
    )

    print(
        f"Clean RTs         : "
        f"{srt_clean_trials}"
    )

    print(
        f"Misses            : "
        f"{srt_misses}"
    )

    print(
        f"Anticipations     : "
        f"{n_anticipations}"
    )

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

    print(
        f"CV                 : "
        f"{cv_adjusted_rt:.3f}"
    )

    print(
        f"Fastest RT         : "
        f"{min_adjusted_rt * 1000:.1f} ms"
    )

    print(
        f"Slowest RT         : "
        f"{max_adjusted_rt * 1000:.1f} ms"
    )

    # ==================================================
    # PRINT MODALITY SUMMARY
    # ==================================================

    print(
        "\n-----------------------------------"
    )

    print(
        " SRT by Stimulus Modality"
    )

    print(
        "-----------------------------------"
    )

    print(
        f"Auditory Only      : "
        f"{modality_results['Audio_Mean_RT_ms']:.1f} ms "
        f"(n={modality_results['Audio_N']})"
    )

    print(
        f"Visual Only        : "
        f"{modality_results['Visual_Mean_RT_ms']:.1f} ms "
        f"(n={modality_results['Visual_N']})"
    )

    print(
        f"Audiovisual        : "
        f"{modality_results['Audiovisual_Mean_RT_ms']:.1f} ms "
        f"(n={modality_results['Audiovisual_N']})"
    )

    if not SRT_QC_OK:

        print(
            "WARNING: SRT failed quality control. "
            "Inspect this participant."
        )

    # ==================================================
    # OVERALL SRT HISTOGRAM
    # ==================================================

    if srt_clean_trials > 0:

        plt.figure(
            figsize=(8, 5)
        )

        plt.hist(
            srt_clean[
                "Adjusted_RT"
            ] * 1000,
            bins=25,
            edgecolor="black"
        )

        plt.xlabel(
            "Adjusted Reaction Time (ms)"
        )

        plt.ylabel(
            "Frequency"
        )

        plt.title(
            "Simple Reaction Time Distribution"
        )

        plt.grid(
            True
        )

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                participant_folder,
                "SRT_Histogram.png"
            ),
            dpi=300
        )

        plt.close()

    # ==================================================
    # SRT BY MODALITY PLOT
    # ==================================================

    if srt_clean_trials > 0:

        plt.figure(
            figsize=(8, 5)
        )

        modality_order = [
            "audio",
            "visual",
            "audiovisual"
        ]

        modality_display = [
            "Auditory Only",
            "Visual Only",
            "Audiovisual"
        ]

        # Fixed random seed makes the visual jitter
        # reproducible every time the analysis is run.
        rng = np.random.default_rng(
            42
        )

        for position, trial_type in enumerate(
            modality_order
        ):

            modality_data = (
                srt_clean[
                    srt_clean[
                        "Trial_Type_Clean"
                    ]
                    == trial_type
                ][
                    "Adjusted_RT"
                ]
                * 1000
            )

            if len(
                modality_data
            ) == 0:

                continue

            # --------------------------------
            # Individual trial points
            # --------------------------------

            jitter = rng.uniform(
                -0.08,
                0.08,
                size=len(
                    modality_data
                )
            )

            x_positions = (
                np.full(
                    len(
                        modality_data
                    ),
                    position
                )
                + jitter
            )

            plt.scatter(
                x_positions,
                modality_data,
                alpha=0.35,
                s=18
            )

            # --------------------------------
            # Mean
            # --------------------------------

            mean_rt = (
                modality_data.mean()
            )

            plt.scatter(
                position,
                mean_rt,
                s=140,
                marker="D",
                edgecolor="black",
                linewidth=1.2,
                zorder=5
            )

            # --------------------------------
            # Mean value label
            # --------------------------------

            plt.text(
                position,
                mean_rt,
                f"  {mean_rt:.1f} ms",
                va="center",
                fontsize=9
            )

        plt.xticks(
            range(
                len(
                    modality_order
                )
            ),
            modality_display
        )

        plt.ylabel(
            "Adjusted Reaction Time (ms)"
        )

        plt.xlabel(
            "Stimulus Modality"
        )

        plt.title(
            "Simple Reaction Time by Stimulus Modality"
        )

        plt.grid(
            axis="y",
            alpha=0.3
        )

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                participant_folder,
                "SRT_By_Modality.png"
            ),
            dpi=300
        )

        plt.close()

    # ==================================================
    # RETURN RESULTS TO MAIN ANALYSIS
    # ==================================================

    return {

        # -------------------------
        # Overall SRT
        # -------------------------

        "SRT_Trials":
            srt_trials,

        "SRT_Valid_Trials":
            srt_valid_trials,

        "SRT_Clean_Trials":
            srt_clean_trials,

        "SRT_Misses":
            srt_misses,

        "SRT_Anticipations":
            n_anticipations,

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
            SRT_QC_OK,

        # -------------------------
        # Auditory Only
        # -------------------------

        "Audio_N":
            modality_results[
                "Audio_N"
            ],

        "Audio_Mean_RT_ms":
            modality_results[
                "Audio_Mean_RT_ms"
            ],

        "Audio_Median_RT_ms":
            modality_results[
                "Audio_Median_RT_ms"
            ],

        "Audio_SD_RT_ms":
            modality_results[
                "Audio_SD_RT_ms"
            ],

        "Audio_Fastest_RT_ms":
            modality_results[
                "Audio_Fastest_RT_ms"
            ],

        "Audio_Slowest_RT_ms":
            modality_results[
                "Audio_Slowest_RT_ms"
            ],

        # -------------------------
        # Visual Only
        # -------------------------

        "Visual_N":
            modality_results[
                "Visual_N"
            ],

        "Visual_Mean_RT_ms":
            modality_results[
                "Visual_Mean_RT_ms"
            ],

        "Visual_Median_RT_ms":
            modality_results[
                "Visual_Median_RT_ms"
            ],

        "Visual_SD_RT_ms":
            modality_results[
                "Visual_SD_RT_ms"
            ],

        "Visual_Fastest_RT_ms":
            modality_results[
                "Visual_Fastest_RT_ms"
            ],

        "Visual_Slowest_RT_ms":
            modality_results[
                "Visual_Slowest_RT_ms"
            ],

        # -------------------------
        # Audiovisual
        # -------------------------

        "Audiovisual_N":
            modality_results[
                "Audiovisual_N"
            ],

        "Audiovisual_Mean_RT_ms":
            modality_results[
                "Audiovisual_Mean_RT_ms"
            ],

        "Audiovisual_Median_RT_ms":
            modality_results[
                "Audiovisual_Median_RT_ms"
            ],

        "Audiovisual_SD_RT_ms":
            modality_results[
                "Audiovisual_SD_RT_ms"
            ],

        "Audiovisual_Fastest_RT_ms":
            modality_results[
                "Audiovisual_Fastest_RT_ms"
            ],

        "Audiovisual_Slowest_RT_ms":
            modality_results[
                "Audiovisual_Slowest_RT_ms"
            ]
    }