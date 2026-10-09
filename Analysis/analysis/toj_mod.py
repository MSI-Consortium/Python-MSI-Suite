"""Analysis for modified Temporal Order Judgment (TOJ_Mod).

TOJ_Mod contains three distinct temporal-order judgments:
  visual      : 1 = LEFT first, 2 = RIGHT first
  auditory    : 1 = HIGH pitch first, 2 = LOW pitch first
  audiovisual : 1 = AUDIO first, 2 = VISUAL first

Each available modality is fit separately.  The psychometric x-axis is recoded so
negative values mean response-category 1 was physically first and positive values
mean response-category 2 was physically first.  Therefore the fitted 50% point is
an interpretable PSS for every modality.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


def _logistic(x, pss, slope):
    slope = np.maximum(np.abs(slope), 1e-6)
    z = np.clip((np.asarray(x, dtype=float) - pss) / slope, -60, 60)
    return 1.0 / (1.0 + np.exp(-z))


def _signed_soa(df, modality):
    soa = pd.to_numeric(df["SOA"], errors="coerce").abs()
    side = df["Side"].astype(str).str.lower().str.strip()
    raw_soa = pd.to_numeric(df["SOA"], errors="coerce")
    if modality == "visual":
        # category 1 = left first; category 2 = right first
        return np.where(side.eq("left"), -soa, soa)
    if modality == "auditory":
        # category 1 = high first; category 2 = low first
        # Backward compatibility: old files may encode high/low as right/left.
        is_high = side.isin(["high", "right"])
        return np.where(is_high, -soa, soa)
    # audiovisual: runner defines negative = audio first, positive = visual first
    return raw_soa.to_numpy(dtype=float)


def _catch_correct(row, modality):
    response = pd.to_numeric(pd.Series([row.get("Response")]), errors="coerce").iloc[0]
    if pd.isna(response):
        return False
    response = int(response)
    side = str(row.get("Side", "")).lower().strip()
    soa = pd.to_numeric(pd.Series([row.get("SOA")]), errors="coerce").iloc[0]
    if modality == "visual":
        expected = 1 if side == "left" else 2
    elif modality == "auditory":
        expected = 1 if side in ("high", "right") else 2
    else:
        expected = 1 if soa < 0 else 2
    return response == expected


def _safe_fit(x, y):
    if len(np.unique(x)) < 3 or len(np.unique(y)) < 2:
        return np.nan, np.nan, np.nan, None
    try:
        p0 = [0.0, max(20.0, float(np.nanstd(x)) / 2)]
        bounds = ([-2000.0, 1.0], [2000.0, 5000.0])
        pars, _ = curve_fit(_logistic, x, y, p0=p0, bounds=bounds, maxfev=30000)
        pred = _logistic(x, *pars)
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
        return float(pars[0]), float(abs(pars[1])), r2, pars
    except Exception as exc:
        print(f"TOJ_Mod fit failed: {exc}")
        return np.nan, np.nan, np.nan, None


def _analyze_modality(data, modality, output_folder, min_r2, max_slope_ms,
                      min_response_proportion, max_response_proportion):
    d = data.copy()
    d["Response"] = pd.to_numeric(d["Response"], errors="coerce")
    d["SOA"] = pd.to_numeric(d["SOA"], errors="coerce")
    d = d[d["Response"].isin([1, 2]) & d["SOA"].notna()].copy()
    prefix = f"TOJ_Mod_{modality.capitalize()}"
    if d.empty:
        return {}

    d["Signed_SOA"] = _signed_soa(d, modality)
    d["Category2"] = (d["Response"] == 2).astype(float)
    catch = d[d["SOA"].abs() >= 1000].copy()
    experimental = d[d["SOA"].abs() < 1000].copy()

    grouped = experimental.groupby("Signed_SOA", as_index=False)["Category2"].agg(["mean", "count"]).reset_index()
    x = grouped["Signed_SOA"].to_numpy(dtype=float)
    y = grouped["mean"].to_numpy(dtype=float)
    pss, slope, r2, pars = _safe_fit(x, y)

    p2 = float(experimental["Category2"].mean()) if len(experimental) else np.nan
    p1 = 1.0 - p2 if np.isfinite(p2) else np.nan
    response_range_ok = bool(np.isfinite(p2) and min_response_proportion <= p2 <= max_response_proportion)
    response_bias_ok = response_range_ok
    fit_ok = bool(np.isfinite(r2) and r2 >= min_r2 and np.isfinite(slope) and slope <= max_slope_ms)
    catch_correct = int(sum(_catch_correct(row, modality) for _, row in catch.iterrows()))
    catch_trials = int(len(catch))
    catch_ok = bool(catch_trials == 0 or catch_correct / catch_trials >= 0.80)

    # Conventional JND = half the separation between 25% and 75%
    # thresholds of the fitted logistic psychometric function.
    soa_25 = pss - np.log(3) * slope if np.isfinite(slope) else np.nan
    soa_75 = pss + np.log(3) * slope if np.isfinite(slope) else np.nan
    jnd = (soa_75 - soa_25) / 2 if np.isfinite(soa_25) else np.nan

    # Raw plot
    plt.figure(figsize=(8, 5))
    plt.scatter(x, y)
    plt.axhline(0.5, linestyle="--")
    plt.axvline(0, linestyle="--")
    plt.ylim(-0.05, 1.05)
    plt.xlabel("Signed SOA (ms)")
    plt.ylabel("Proportion category-2 responses")
    plt.title(f"TOJ_Mod {modality.capitalize()} - Raw")
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f"TOJ_Mod_{modality.capitalize()}_Raw.png"), dpi=150)
    plt.close()

    # Fitted plot
    plt.figure(figsize=(8, 5))
    plt.scatter(x, y)
    if pars is not None:
        xx = np.linspace(float(np.min(x)), float(np.max(x)), 400)
        plt.plot(xx, _logistic(xx, *pars))
        plt.axvline(pss, linestyle="--")
    plt.axhline(0.5, linestyle="--")
    plt.ylim(-0.05, 1.05)
    plt.xlabel("Signed SOA (ms)")
    plt.ylabel("Proportion category-2 responses")
    plt.title(f"TOJ_Mod {modality.capitalize()} - Fitted")
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f"TOJ_Mod_{modality.capitalize()}_Fitted.png"), dpi=150)
    plt.close()

    return {
        f"{prefix}_Trials": int(len(d)),
        f"{prefix}_PSS_ms": pss,
        f"{prefix}_JND_ms": jnd,  # conventional 25%-75% JND
        f"{prefix}_JND_25_75_ms": jnd,
        f"{prefix}_Logistic_Scale_ms": slope,
        f"{prefix}_SOA_25_ms": soa_25,
        f"{prefix}_SOA_75_ms": soa_75,
        f"{prefix}_Slope_ms": slope,
        f"{prefix}_R2": r2,
        f"{prefix}_Category1_Proportion": p1,
        f"{prefix}_Category2_Proportion": p2,
        f"{prefix}_Fit_OK": fit_ok,
        f"{prefix}_Response_Range_OK": response_range_ok,
        f"{prefix}_Response_Bias_OK": response_bias_ok,
        f"{prefix}_Catch_Correct": catch_correct,
        f"{prefix}_Catch_Trials": catch_trials,
        f"{prefix}_Catch_OK": catch_ok,
        f"{prefix}_QC_OK": bool(fit_ok and response_range_ok and response_bias_ok and catch_ok),
    }


def analyze_toj_mod(toj_mod, output_folder, min_r2=0.80, max_slope_ms=500,
                    min_response_proportion=0.10, max_response_proportion=0.90):
    """Analyze each available TOJ_Mod modality separately and return one result dict."""
    os.makedirs(output_folder, exist_ok=True)
    results = {"TOJ_Mod_Trials": int(len(toj_mod))}
    modality_qc = []
    available = []

    for modality in ("visual", "auditory", "audiovisual"):
        subset = toj_mod[toj_mod["Trial_Type"].astype(str).str.lower().eq(modality)].copy()
        if subset.empty:
            continue
        available.append(modality)
        mod_results = _analyze_modality(
            subset, modality, output_folder, min_r2, max_slope_ms,
            min_response_proportion, max_response_proportion
        )
        results.update(mod_results)
        modality_qc.append(bool(mod_results.get(f"TOJ_Mod_{modality.capitalize()}_QC_OK", False)))

    results["TOJ_Mod_Modalities"] = ", ".join(available)
    results["TOJ_Mod_QC_OK"] = bool(modality_qc and all(modality_qc))
    return results
