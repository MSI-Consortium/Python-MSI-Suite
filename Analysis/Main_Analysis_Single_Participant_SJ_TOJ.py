import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import os

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

#import data
df = pd.read_csv("../Data/Participant_003/data_003_19_f_vandy_offline_20260717_165618.csv")

#Separate the 3 data sets
sj = df[df["Experiment"] == "sj"].copy()
toj = df[df["Experiment"] == "toj"].copy()
srt = df[df["Experiment"] == "srt"].copy()

#Gives the Number of trials Per data set
print("SJ trials:", len(sj))
print("TOJ trials:", len(toj))
print("SRT trials:", len(srt))

#Convert Responses to binary variables
sj["Simultaneous"] = (sj["Response"] == 1).astype(int)
toj["Visual_First"] = (toj["Response"] == 2).astype(int)

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
params, covariance = curve_fit(
    gaussian,
    x,
    y,
    p0=initial_guess
)
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

#Saving the SJ Results
sj_results = pd.DataFrame({
    "Peak_Probability": [A],
    "PSS_ms": [PSS],
    "Sigma_ms": [sigma],
    "TBW_ms": [TBW],
    "R2": [r_squared]
})
sj_results.to_csv("Results/SJ_Results.csv", index=False)

####Paramerters Summary
print("\n===================================")
print(" SJ Psychometric Analysis")
print("===================================")

print(f"Peak Probability : {A*100:.1f}%")
print(f"PSS              : {PSS:.2f} ms")
print(f"Sigma            : {sigma:.2f} ms")
print(f"TBW (FWHM)       : {TBW:.2f} ms")
print(f"R²               : {r_squared:.3f}")
plt.figure(figsize=(8,5))
plt.scatter(
    x,
    y,
    color="blue",
    label="Observed Data"
)
plt.plot(
    xx,
    yy,
    color="red",
    linewidth=2,
    label="Gaussian Fit"
)
plt.xlabel("SOA (ms)")
plt.ylabel("Probability Simultaneous")
plt.title("Simultaneity Judgment")
plt.legend()
plt.grid(True)
#save plot
plt.tight_layout()
plt.savefig("Results/SJ_Gaussian_Fit.png", dpi=300)
#print/show plot
plt.show()

####Print SJ Summary
# print("\nSJ Summary")
# print(sj_summary)
# print("\nSJ Response Counts")
# print(sj["Response"].value_counts())
# print(pd.crosstab(sj["SOA"], sj["Response"]))

####Basic fitted SJ plot
plt.figure(figsize=(6,4))
plt.plot(
    sj_summary["SOA"],
    sj_summary["P_Simultaneous"],
    "o-"
)
plt.xlabel("SOA (ms)")
plt.ylabel("Probability Simultaneous")
plt.title("SJ Psychometric Function")
plt.grid(True)
plt.show()



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
params_toj, covariance_toj = curve_fit(
    logistic,
    x_toj,
    y_toj,
    p0=initial_guess
)

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

#Saving the TOJ Results
toj_results = pd.DataFrame({
    "PSS_ms":[PSS_toj],
    "Slope":[slope],
    "JND_ms":[JND],
    "R2":[r_squared_toj]
})
toj_results.to_csv(
    "Results/TOJ_Results.csv",
    index=False
)

# Create plot
plt.figure(figsize=(8,5))
plt.scatter(
    x_toj,
    y_toj,
    color="blue",
    label="Observed Data"
)
plt.plot(
    xx_toj,
    yy_toj,
    color="red",
    linewidth=2,
    label="Logistic Fit"
)
plt.xlabel("SOA (ms)")
plt.ylabel("Probability Visual First")
plt.title("Temporal Order Judgment")
plt.legend()
plt.grid(True)
plt.tight_layout()
# #Save Plot
plt.savefig(
    "Results/TOJ_Logistic_Fit.png",
    dpi=300
)
plt.show()

#Print TOJ Summary and Plot
#print("\nTOJ Summary")
#print(toj_summary)
#print("\nTOJ Response Counts")
#print(toj["Response"].value_counts())
#print(pd.crosstab(toj["SOA"], toj["Response"]))

####Basic TOJ Fitted TOJ plot
plt.figure(figsize=(6,4))
plt.plot(
    toj_summary["SOA"],
    toj_summary["P_Visual_First"],
    "o-"
)
plt.xlabel("SOA (ms)")
plt.ylabel("Probability Visual First")
plt.title("TOJ Psychometric Function")
plt.grid(True)
plt.show()

