import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilenames

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

MAX_CV = None


# Create Results folder if it doesn't exist
os.makedirs("Results", exist_ok=True)

#Define Gaussian Function - SJ
def gaussian(x, A, mu, sigma):
    """
    Gaussian function for Simultaneity Judgment
    A     = Peak probability
    mu    = Point of Subjective Simultaneity (PSS)
    sigma = Width of the curve
    """
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

#Define Logistic Function - TOJ
def logistic(x, PSS, slope):
    """
    Logistic psychometric function for Temporal Order Judgment

    PSS   = Point of Subjective Simultaneity
    slope = Controls steepness of the curve
    """

    return 1 / (1 + np.exp(-(x - PSS) / slope))

####################################################
# Select participant files
####################################################
root = Tk()
root.withdraw()
selected_files = askopenfilenames(
    title="Select Participant CSV Files",
    initialdir="../Data",
    filetypes=[("CSV Files","*.csv")]
)
root.destroy()
print(selected_files)

####################################################
# Store results for all participants
####################################################
master_results = []

#### The analysis being done
def analyze_participant(df, participant_name):

    global master_results

    # Create participant results folder
    participant_folder = os.path.join("Results", participant_name)
    os.makedirs(participant_folder, exist_ok=True)

    #Separate the 3 data sets
    sj = df[df["Experiment"] == "sj"].copy()
    toj = df[df["Experiment"] == "toj"].copy()
    srt = df[df["Experiment"] == "srt"].copy()

    # Trial Counts
    sj_trials = len(sj)
    toj_trials = len(toj)
    srt_trials = len(srt)

    sj_valid_trials = sj["Response"].notna().sum()
    toj_valid_trials = toj["Response"].notna().sum()
    srt_valid_trials = srt["Reaction_Time"].notna().sum()

    # Extracting Participant Information
    participant_id = df["Participant_ID"].iloc[0]
    age = df["Age"].iloc[0]
    gender = df["Gender"].iloc[0]
    site = df["Site"].iloc[0]

    #Gives the Number of trials Per data set
    print("SJ trials:", len(sj))
    print("TOJ trials:", len(toj))
    print("SRT trials:", len(srt))

    #Convert Responses to binary variables
    sj["Simultaneous"] = (sj["Response"] == 1).astype(int)
    toj["Visual_First"] = (toj["Response"] == 2).astype(int)

    # Response Distribution
    sj_response_counts = sj["Response"].value_counts()
    toj_response_counts = toj["Response"].value_counts()

    sj_simultaneous = sj_response_counts.get(1, 0)
    sj_not_simultaneous = sj_response_counts.get(2, 0)

    toj_audio_first = toj_response_counts.get(1, 0)
    toj_visual_first = toj_response_counts.get(2, 0)

    # Response Proportions
    SJ_Simultaneous_Proportion = sj_simultaneous / sj_trials
    SJ_Not_Simultaneous_Proportion = sj_not_simultaneous / sj_trials

    TOJ_Audio_First_Proportion = toj_audio_first / toj_trials
    TOJ_Visual_First_Proportion = toj_visual_first / toj_trials

    # Response Range Quality Checks
    SJ_Response_Range_OK = (
            sj_simultaneous > 0 and
            sj_not_simultaneous > 0
    )
    TOJ_Response_Range_OK = (
            toj_audio_first > 0 and
            toj_visual_first > 0
    )
    SJ_Response_Bias_OK = (
            MIN_RESPONSE_PROPORTION <= sj_simultaneous / sj_trials <= MAX_RESPONSE_PROPORTION
    )
    TOJ_Response_Bias_OK = (
            MIN_RESPONSE_PROPORTION <= toj_visual_first / toj_trials <= MAX_RESPONSE_PROPORTION
    )
    if not SJ_Response_Range_OK:
        print("\nWARNING: Participant used only one SJ response.")

    if not TOJ_Response_Range_OK:
        print("\nWARNING: Participant used only one TOJ response.")

    ####SJ Analysis
    #SJ Summary
    #Mean = Probability of responding "Simultaneous"
    sj_summary = (
        sj.groupby("SOA")["Simultaneous"]
          .agg(
              P_Simultaneous="mean",
              Trials="count"
          )
          .reset_index()
    )
    ##SJ Gaussian Fit
    x = sj_summary["SOA"].values
    y = sj_summary["P_Simultaneous"].values
    initial_guess = [
        max(y),                 # Peak probability
        x[np.argmax(y)],        # SOA with highest probability
        150                     # Initial sigma estimate (ms)
    ]

    try:
        params, covariance = curve_fit(
            gaussian,
            x,
            y,
            p0=initial_guess
        )

    except RuntimeError:

        print(f"WARNING: SJ fit failed for Participant {participant_id}")

        return

    A, PSS, sigma = params
    TBW = 2.355 * sigma
    xx = np.linspace(-300,300,500)
    yy = gaussian(xx,*params)

    # Predicted values at the observed SOAs
    y_fit = gaussian(x, *params)

    # Goodness of fit (R²)
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)

    # SJ Quality Flag
    SJ_Fit_OK = (
            r_squared >= MIN_R2 and
            sigma > 0 and
            sigma < MAX_SIGMA_MS
    )

    #Saving the SJ Results
    sj_results = pd.DataFrame({
        "Peak_Probability": [A],
        "PSS_ms": [PSS],
        "Sigma_ms": [sigma],
        "TBW_ms": [TBW],
        "R2": [r_squared]
    })
    sj_results.to_csv(
        os.path.join(participant_folder, "SJ_Results.csv"),
        index=False
    )

    ####Paramerters Summary
    print("\n===================================")
    print(" SJ Psychometric Analysis")
    print("===================================")

    print(f"Peak Probability : {A*100:.1f}%")
    print(f"PSS              : {PSS:.2f} ms")
    print(f"Sigma            : {sigma:.2f} ms")
    print(f"TBW (FWHM)       : {TBW:.2f} ms")
    print(f"R²               : {r_squared:.3f}")
    if not SJ_Fit_OK:
        print("WARNING: SJ fit is poor. Inspect this participant.")

    # plt.figure(figsize=(8,5))
    # plt.scatter(
    #     x,
    #     y,
    #     color="blue",
    #     label="Observed Data"
    # )
    # plt.plot(
    #     xx,
    #     yy,
    #     color="red",
    #     linewidth=2,
    #     label="Gaussian Fit"
    # )
    # plt.xlabel("SOA (ms)")
    # plt.ylabel("Probability Simultaneous")
    # plt.title("Simultaneity Judgment")
    # plt.legend()
    # plt.grid(True)
    # #save plot
    # #plt.tight_layout()
    # #plt.savefig(
    #     os.path.join(participant_folder, "SJ_Gaussian_Fit.png"),
    #     dpi=300
    # )
    # #print/show plot
    # plt.show()

    ####Print SJ Summary
    # print("\nSJ Summary")
    # print(sj_summary)
    # print("\nSJ Response Counts")
    # print(sj["Response"].value_counts())
    # print(pd.crosstab(sj["SOA"], sj["Response"]))

    ####Basic fitted SJ plot
    # plt.figure(figsize=(6,4))
    # plt.plot(
    #     sj_summary["SOA"],
    #     sj_summary["P_Simultaneous"],
    #     "o-"
    # )
    # plt.xlabel("SOA (ms)")
    # plt.ylabel("Probability Simultaneous")
    # plt.title("SJ Psychometric Function")
    # plt.grid(True)
    # plt.show()


    ####TOJ Analysis
    #TOJ Summary
    toj_summary = (
        toj.groupby("SOA")["Visual_First"]
           .agg(
                P_Visual_First="mean",
                Trials="count"
           )
           .reset_index()
    )

    # TOJ Logistic Fit
    x_toj = toj_summary["SOA"].values
    y_toj = toj_summary["P_Visual_First"].values

    initial_guess = [
        0,      # PSS
        50      # slope
    ]
    #fit logistic curve
    try:
        params_toj, covariance_toj = curve_fit(
        logistic,
        x_toj,
        y_toj,
        p0=initial_guess
    )
    except RuntimeError:

        print(f"WARNING: TOJ fit failed for Participant {participant_id}")

        return

    #Extract The Parameters
    PSS_toj, slope = params_toj

    #Create a smooth curve
    xx_toj = np.linspace(-300,300,500)
    yy_toj = logistic(xx_toj,*params_toj)

    #Calculate R2
    y_fit_toj = logistic(x_toj,*params_toj)
    ss_res = np.sum((y_toj-y_fit_toj)**2)
    ss_tot = np.sum((y_toj-np.mean(y_toj))**2)
    r_squared_toj = 1-(ss_res/ss_tot)

    # TOJ Quality Flag
    TOJ_Fit_OK = (
            r_squared_toj >= MIN_R2 and
            slope > 0 and
            slope < MAX_SLOPE_MS
    )

    #Calculate the JND
    JND = np.log(3) * slope

    ####Paramerters Summary
    print("\n===================================")
    print(" TOJ Psychometric Analysis")
    print("===================================")

    print(f"PSS        : {PSS_toj:.2f} ms")
    print(f"Slope      : {slope:.2f}")
    print(f"JND        : {JND:.2f} ms")
    print(f"R²         : {r_squared_toj:.3f}")
    if not TOJ_Fit_OK:
        print("WARNING: TOJ fit is poor. Inspect this participant.")

    #Saving the TOJ Results
    toj_results = pd.DataFrame({
        "PSS_ms":[PSS_toj],
        "Slope":[slope],
        "JND_ms":[JND],
        "R2":[r_squared_toj]
    })
    toj_results.to_csv(
        os.path.join(participant_folder, "TOJ_Results.csv"),
        index=False
    )

    #Create plot
    # plt.figure(figsize=(8,5))
    # plt.scatter(
    #     x_toj,
    #     y_toj,
    #     color="blue",
    #     label="Observed Data"
    # )
    # plt.plot(
    #     xx_toj,
    #     yy_toj,
    #     color="red",
    #     linewidth=2,
    #     label="Logistic Fit"
    # )
    # plt.xlabel("SOA (ms)")
    # plt.ylabel("Probability Visual First")
    # plt.title("Temporal Order Judgment")
    # plt.legend()
    # plt.grid(True)
    # plt.tight_layout()
    # #Save Plot
    # plt.savefig(
    #     os.path.join(participant_folder, "TOJ_Logistic_Fit.png"),
    #     dpi=300
    # )
    # plt.show()

    #Print TOJ Summary and Plot
    #print("\nTOJ Summary")
    #print(toj_summary)
    #print("\nTOJ Response Counts")
    #print(toj["Response"].value_counts())
    #print(pd.crosstab(toj["SOA"], toj["Response"]))

    ####Basic TOJ Fitted TOJ plot
    # plt.figure(figsize=(6,4))
    # plt.plot(
    #     toj_summary["SOA"],
    #     toj_summary["P_Visual_First"],
    #     "o-"
    # )
    # plt.xlabel("SOA (ms)")
    # plt.ylabel("Probability Visual First")
    # plt.title("TOJ Psychometric Function")
    # plt.grid(True)
    # plt.show()

    #SRT Analysis
    #IMPORTANT: All RTs use Adjusted RTs
    # Keep only trials with a valid reaction time
    srt_valid = srt.dropna(subset=["Adjusted_RT"]).copy()

    # SRT Trial Counts
    srt_total_trials = len(srt)
    srt_valid_trials = len(srt_valid)
    srt_misses = srt_total_trials - srt_valid_trials

    # Remove anticipatory responses
    anticipation_threshold = MIN_RT_MS / 1000
    anticipations = srt_valid[
        srt_valid["Adjusted_RT"] < anticipation_threshold
        ]
    n_anticipations = len(anticipations)
    srt_clean = srt_valid[
        srt_valid["Adjusted_RT"] >= anticipation_threshold
        ].copy()

    # SRT Summary Statistics
    mean_adjusted_rt = srt_clean["Adjusted_RT"].mean()
    median_adjusted_rt = srt_clean["Adjusted_RT"].median()
    sd_adjusted_rt = srt_clean["Adjusted_RT"].std()
    cv_adjusted_rt = sd_adjusted_rt / mean_adjusted_rt
    min_adjusted_rt = srt_clean["Adjusted_RT"].min()
    max_adjusted_rt = srt_clean["Adjusted_RT"].max()

    # SRT Quality Control
    SRT_QC_OK = (
            srt_valid_trials >= MIN_VALID_SRT_TRIALS and
            n_anticipations <= MAX_ANTICIPATIONS and
            MIN_MEAN_RT_SEC <= mean_adjusted_rt <= MAX_MEAN_RT_SEC
    )

    # Save SRT Results
    srt_results = pd.DataFrame({
        "Trials": [srt_trials],
        "Valid_Trials": [srt_valid_trials],
        "Misses": [srt_misses],
        "Anticipations": [n_anticipations],
        "Mean_Adjusted_RT_ms": [mean_adjusted_rt * 1000],
        "Median_Adjusted_RT_ms": [median_adjusted_rt * 1000],
        "SD_Adjusted_RT_ms": [sd_adjusted_rt * 1000],
        "CV_Adjusted_RT": [cv_adjusted_rt],
        "Fastest_RT_ms": [min_adjusted_rt * 1000],
        "Slowest_RT_ms": [max_adjusted_rt * 1000],
        "SRT_QC_OK": [SRT_QC_OK]
    })

    srt_results.to_csv(
        os.path.join(
            participant_folder,
            "SRT_Results.csv"
        ),
        index=False
    )
    #Paramerters Summary
    print("\n===================================")
    print(" SRT Analysis")
    print("===================================")

    print(f"Trials            : {srt_total_trials}")
    print(f"Valid RTs         : {len(srt_clean)}")
    print(f"Misses            : {srt_misses}")
    print(f"Anticipations     : {n_anticipations}")

    print(f"Mean Adjusted RT   : {mean_adjusted_rt * 1000:.1f} ms")
    print(f"Median Adjusted RT : {median_adjusted_rt * 1000:.1f} ms")
    print(f"SD Adjusted RT     : {sd_adjusted_rt * 1000:.1f} ms")
    print(f"CV                 : {cv_adjusted_rt:.3f}")
    print(f"Fastest RT         : {min_adjusted_rt * 1000:.1f} ms")
    print(f"Slowest RT         : {max_adjusted_rt * 1000:.1f} ms")

    # SRT Histogram
    plt.figure(figsize=(8, 5))
    plt.hist(
        srt_clean["Adjusted_RT"] * 1000,
        bins=25,
        edgecolor="black"
    )
    plt.xlabel("Adjusted Reaction Time (ms)")
    plt.ylabel("Frequency")
    plt.title("Simple Reaction Time Distribution")
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

    # Overall Participant Quality Flag
    Participant_OK = (
            SJ_Fit_OK and
            TOJ_Fit_OK and
            SJ_Response_Range_OK and
            TOJ_Response_Range_OK and
            SJ_Response_Bias_OK and
            TOJ_Response_Bias_OK
    )

    ####################################################
    # Add participant to master results
    ####################################################
    participant_summary = {
        "Participant_ID": participant_id,
        "Age": age,
        "Gender": gender,
        "Site": site,
        "Group": "",

        "Participant_OK": Participant_OK,
        "SJ_Simultaneous": sj_simultaneous,
        "SJ_Not_Simultaneous": sj_not_simultaneous,
        "SJ_Simultaneous_Proportion": SJ_Simultaneous_Proportion,
        "SJ_Not_Simultaneous_Proportion": SJ_Not_Simultaneous_Proportion,
        "SJ_Response_Range_OK": SJ_Response_Range_OK,
        "SJ_Response_Bias_OK": SJ_Response_Bias_OK,
        "TOJ_Audio_First": toj_audio_first,
        "TOJ_Visual_First": toj_visual_first,"TOJ_Audio_First_Proportion": TOJ_Audio_First_Proportion,
        "TOJ_Visual_First_Proportion": TOJ_Visual_First_Proportion,
        "TOJ_Response_Range_OK": TOJ_Response_Range_OK,
        "TOJ_Response_Bias_OK": TOJ_Response_Bias_OK,

        "SJ_Trials": sj_trials,
        "SJ_Valid_Trials": sj_valid_trials,
        "SJ_PSS_ms": PSS,
        "SJ_TBW_ms": TBW,
        "SJ_R2": r_squared,
        "SJ_Fit_OK": SJ_Fit_OK,

        "TOJ_Trials": toj_trials,
        "TOJ_Valid_Trials": toj_valid_trials,
        "TOJ_PSS_ms": PSS_toj,
        "TOJ_JND_ms": JND,
        "TOJ_R2": r_squared_toj,
        "TOJ_Fit_OK": TOJ_Fit_OK,

        "SRT_Trials": srt_trials,
        "SRT_Valid_Trials": srt_valid_trials,
        "SRT_Misses": srt_misses,
        "SRT_Anticipations": n_anticipations,
        "Mean_Adjusted_RT_ms": mean_adjusted_rt * 1000,
        "Median_Adjusted_RT_ms": median_adjusted_rt * 1000,
        "SD_Adjusted_RT_ms": sd_adjusted_rt * 1000,
        "CV_Adjusted_RT": cv_adjusted_rt,
        "SRT_QC_OK": SRT_QC_OK,
    }
    master_results.append(participant_summary)

####################################################
# Analyze each participant
#"analyze_participant" w/ def analyze_participant directly above allows to the loop to only need to read 5 lines of cod instead of the 100+ cod that is under the :"def" that it is actually running.
####################################################
for file in selected_files:
    print("\n==============================")
    print(f"Analyzing: {os.path.basename(file)}")
    participant_df = pd.read_csv(file)
    participant_name = os.path.splitext(os.path.basename(file))[0]
    analyze_participant(participant_df, participant_name)

####################################################
# Save master spreadsheet
####################################################

master_df = pd.DataFrame(master_results)
master_df.to_csv(
    "Results/Master_Results.csv",
    index=False
)
print("\n===================================")
print("Master results saved!")
print("===================================")
print(master_df)