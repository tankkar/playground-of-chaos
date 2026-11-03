import pandas as pd
import matplotlib.pyplot as plt

# ─── 1) Load data ─────────────────────────────────────────────────────────────
df = pd.read_csv('169_sample_normalised_depth.csv')

# ─── 2) Filter data ────────────────────────────────────────────────────────────
df = df[df['Median Depth QC Status'] == "Pass"]

# ─── 3) Define regions ────────────────────────────────────────────────────────
region1_cols = [
    "chr16:170201-170400", "chr16:170401-170600", "chr16:170601-170800",
    "chr16:170801-171000", "chr16:171001-171200", "chr16:171201-171400",
    "chr16:171401-171600", "chr16:171601-171800", "chr16:171801-172000"
]

region2_cols = [
    "chr16:174001-174200", "chr16:174201-174400", "chr16:174401-174600",
    "chr16:174601-174800", "chr16:174801-175000", "chr16:175001-175200",
    "chr16:175201-175400", "chr16:175401-175600"
]

# ─── 4) Compute mean columns ──────────────────────────────────────────────────
df['normalised mean r1'] = df[region1_cols].mean(axis=1)
df['normalised mean r2'] = df[region2_cols].mean(axis=1)

df = df[df['normalised mean r2'] < 1.5]
# ─── 5) Define group color mapping (your preferred colors) ────────────────────
first_label_colors = {
    '--': '#ff7f0e',
    '-α3.7': '#2ca02c',
    '-α4.2': '#d62728',
    'CONTROL': '#1f77b4'
}

# ─── 6) Create scatter plot ───────────────────────────────────────────────────
plt.figure(figsize=(8, 6))

for group in df['Group'].unique():
    subset = df[df['Group'] == group]
    plt.scatter(
        subset['normalised mean r1'],
        subset['normalised mean r2'],
        label=group,
        color=first_label_colors[group],
        alpha=0.8,   # as requested
        s=50
    )

plt.xlabel('normalised mean r1')
plt.ylabel('normalised mean r2')
plt.legend(title="Group", loc='upper right')
plt.grid(True, linestyle='--', alpha=0.5)
plt.xlim(0, 2.5)
plt.ylim(0, 2.5)
plt.xticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
plt.yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
# ─── 7) Save and show ─────────────────────────────────────────────────────────
plt.savefig("normalised_normalised mean r1_r2.png", dpi=700, bbox_inches='tight')
plt.show()



import os
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestCentroid
from sklearn.metrics import pairwise_distances
import matplotlib
matplotlib.use("Agg")  # safe in headless envs
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex, hsv_to_rgb

# =========================
# 0) user-config
# =========================
INPUT_CSV  = "200bp_r2_fixed.csv"   # change if needed
OUTPUT_DIR = "plots"                # all plots go here
ENRICHED_CSV = "alpha_depth_enriched.tsv"  # tab-separated enriched output

# axes & styling
XLIMS  = (-0.1, 2.5)              # both axes now match to 2.5
YLIMS  = (-0.1, 2.5)
XTICKS = np.arange(0, 2.6, 0.5)
YTICKS = np.arange(0, 2.6, 0.5)

GROUP_COLORS = {
    "SEA":     "#ff7f0e",
    "3.7K":    "#2ca02c",
    "4.2K":    "#d62728",
    "CONTROL": "#1f77b4",
}

# centroid cross appearance (small neutral crosses)
CENTROID_MARKER = "x"
CENTROID_SIZE = 40         # even smaller per your request
CENTROID_LINEWIDTH = 1.0
CENTROID_ALPHA = 0.9
CENTROID_TEXT_COLOR = "black"
CENTROID_TEXT_FONTSIZE = 8

# =========================
# 1) load & filter
# =========================
os.makedirs(OUTPUT_DIR, exist_ok=True)
df = pd.read_csv(INPUT_CSV)
df = df[df["Median Depth QC Status"] == "Pass"].copy()

# =========================
# 2) define windows & compute means
# =========================
region1_cols = [
    "chr16:170201-170400","chr16:170401-170600","chr16:170601-170800",
    "chr16:170801-171000","chr16:171001-171200","chr16:171201-171400",
    "chr16:171401-171600","chr16:171601-171800","chr16:171801-172000"
]
region2_cols = [
    "chr16:174001-174200","chr16:174201-174400","chr16:174401-174600",
    "chr16:174601-174800","chr16:174801-175000","chr16:175001-175200",
    "chr16:175201-175400","chr16:175401-175600"
]

missing_cols = [c for c in region1_cols + region2_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing expected depth columns: {missing_cols}")

df["normalised mean r1"] = df[region1_cols].mean(axis=1)
df["normalised mean r2"] = df[region2_cols].mean(axis=1)

# =========================
# 3) centroid definitions
# =========================
fine_centroids = {
    "αα/αα":         (1.0, 1.0),
    "αα/ααα3.7":     (1.0, 1.5),
    "αα/ααα4.2":     (1.5, 1.0),
    "ααα3.7/ααα3.7": (1.0, 2.0),
    "ααα4.2/ααα4.2": (2.0, 1.0),

    "--SEA/--SEA":   (0.0, 0.0),
    "--SEA/αα":      (0.5, 0.5),
    "--SEA/-α3.7":   (0.5, 0.0),
    "--SEA/-α4.2":   (0.0, 0.5),
    "--SEA/ααα3.7":  (0.5, 1.0),
    "--SEA/ααα4.2":  (1.0, 0.5),
    "--SEA/αα4.2α3.7": (1.0, 0.0),

    "-α4.2/αα":      (0.5, 1.0),
    "-α4.2/-α4.2":   (0.0, 1.0),
    "-α4.2/-α3.7":   (0.5, 0.5),
    "-α4.2/ααα3.7":  (0.5, 1.5),

    "-α3.7/αα":      (1.0, 0.5),
    "-α3.7/-α3.7":   (1.0, 0.0),
    "-α3.7/-α4.2":   (0.5, 0.5),
    "-α3.7/ααα4.2":  (1.5, 0.5),
}

group_to_centroids = {
    "SEA": [
        "--SEA/--SEA","--SEA/αα","--SEA/-α3.7","--SEA/-α4.2",
        "--SEA/ααα3.7","--SEA/ααα4.2","--SEA/αα4.2α3.7"
    ],
    "3.7K": ["-α3.7/αα","-α3.7/-α3.7","-α3.7/-α4.2","-α3.7/ααα4.2"],
    "4.2K": ["-α4.2/αα","-α4.2/-α4.2","-α4.2/ααα3.7"],
    "CONTROL": ["αα/αα","αα/ααα3.7","αα/ααα4.2","ααα3.7/ααα3.7","ααα4.2/ααα4.2"],
}

# =========================
# Build a clean, highly distinct palette algorithmically
# - Evenly spaced hues in HSV, fixed saturation/value for clarity
# - This produces visually distinct, balanced colors for any N
# =========================
global_genotypes = list(fine_centroids.keys())
N = max(1, len(global_genotypes))
# choose saturation & value for readable, reasonably muted colors
SATURATION = 0.60
VALUE = 0.82
hues = np.linspace(0.0, 1.0, N, endpoint=False)
palette_rgb = [hsv_to_rgb((h, SATURATION, VALUE)) for h in hues]
PALETTE_HEX = [to_hex(c) for c in palette_rgb]
GENO_COLOR_MAP = {g: PALETTE_HEX[i] for i, g in enumerate(global_genotypes)}

# You can quickly inspect the chosen palette by printing:
# print(PALETTE_HEX)

# =========================
# 4) prediction scaffolding
# =========================
df["predicted_genotype"]   = np.nan
df["distance_to_centroid"] = np.nan

def scatter_common(ax):
    ax.set_xlim(*XLIMS)
    ax.set_ylim(*YLIMS)
    ax.set_xticks(XTICKS)
    ax.set_yticks(YTICKS)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_xlabel("normalised mean r1")
    ax.set_ylabel("normalised mean r2")

# =========================
# 5) per-group training, prediction, and plotting (separate images)
# =========================
order = ["SEA","3.7K","4.2K","CONTROL"]
for grp in order:
    sub = df[df["First label"] == grp].copy()
    keys = group_to_centroids[grp]

    # train classifier on group-specific centroids
    X_train = np.array([fine_centroids[k] for k in keys])
    y_train = np.array(keys)
    clf = NearestCentroid().fit(X_train, y_train)

    # predict & min distance
    X_test = sub[["normalised mean r1","normalised mean r2"]].values
    preds = clf.predict(X_test)
    dists = pairwise_distances(X_test, clf.centroids_)
    best_idx = np.argmin(dists, axis=1)
    best_d   = dists[np.arange(len(dists)), best_idx]

    # write back
    df.loc[sub.index, "predicted_genotype"]   = preds
    df.loc[sub.index, "distance_to_centroid"] = best_d

    # ---- (A) first-label scatter (one file) ----
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(sub["normalised mean r1"], sub["normalised mean r2"],
               color=GROUP_COLORS[grp], alpha=0.9)
    ax.set_title(f"{grp} by First label")
    scatter_common(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{grp}_first_label.png"))
    plt.close(fig)

    # ---- (B) predicted-genotype scatter (one file) ----
    genotypes_present = list(dict.fromkeys(preds))  # preserve order of appearance
    fig, ax = plt.subplots(figsize=(8,6))
    for g in genotypes_present:
        mask = (preds == g)
        color = GENO_COLOR_MAP.get(g, "0.4")
        ax.scatter(sub.loc[mask, "normalised mean r1"], sub.loc[mask, "normalised mean r2"],
                   color=color, alpha=0.9, label=g)

    # overlay centroids for that group as neutral small crosses
    for k, (cx, cy) in zip(clf.classes_, clf.centroids_):
        ax.scatter(cx, cy, marker=CENTROID_MARKER, s=CENTROID_SIZE,
                   color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
        ax.text(cx+0.02, cy+0.02, k, fontsize=CENTROID_TEXT_FONTSIZE,
                color=CENTROID_TEXT_COLOR, alpha=0.85)

    ax.set_title(f"{grp} by predicted genotype")
    scatter_common(ax)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{grp}_predicted_genotype.png"))
    plt.close(fig)

    # ---- (C) centroids-only scatter (one file per group) ----
    fig, ax = plt.subplots(figsize=(6,5))
    scatter_common(ax)

    for label, (cx, cy) in zip(clf.classes_, clf.centroids_):
        ax.scatter(cx, cy, marker=CENTROID_MARKER, s=CENTROID_SIZE,
                   color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
        ax.text(cx + 0.02, cy + 0.02, label, fontsize=9,
                color=CENTROID_TEXT_COLOR, alpha=0.95)

    ax.set_title(f"{grp} - group centroids only")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{grp}_centroids_only.png"), dpi=150)
    plt.close(fig)

# =========================
# 6) human-readable mapping & extras
# =========================
descriptive_map = {
    "--SEA/--SEA":   "SEA hom del",
    "--SEA/αα":      "SEA",
    "--SEA/-α3.7":   "SEA 3.7K",
    "--SEA/-α4.2":   "SEA 4.2K",
    "--SEA/ααα3.7":  "SEA + 3.7 dup",
    "--SEA/ααα4.2":  "SEA + 4.2 dup",
    "--SEA/αα4.2α3.7": "SEA + 4.2dup + 3.7del",

    "-α3.7/-α3.7":   "3.7K hom del",
    "-α3.7/αα":      "3.7K",
    "-α3.7/-α4.2":   "3.7+4.2 del",
    "-α3.7/ααα4.2":  "3.7 del+4.2 dup",

    "-α4.2/-α4.2":   "4.2K hom del",
    "-α4.2/αα":      "4.2K",
    "-α4.2/ααα3.7":  "4.2 del+3.7 dup",

    "αα/αα":         "CONTROL",
    "αα/ααα3.7":     "3.7 dup",
    "αα/ααα4.2":     "4.2 dup",
    "ααα3.7/ααα3.7": "3.7 triplication",
    "ααα4.2/ααα4.2": "4.2 triplication",
}
df["translated_genotype"] = df["predicted_genotype"].map(descriptive_map).fillna(df["predicted_genotype"])

# simple ASCII label and α-copy number (optional utilities)
df["simple_genotype"] = (
    df["predicted_genotype"]
      .astype(str)
      .str.replace("α", "a", regex=False)
      .str.replace("-", "", regex=False)
)

def count_alpha(s: str) -> int:
    if not isinstance(s, str):
        return 0
    parts = s.split("/")
    return sum(p.count("α") for p in parts)

df["copy_number"] = df["predicted_genotype"].apply(count_alpha)

# export enriched table
df.to_csv(ENRICHED_CSV, sep="\t", index=False)

# =========================
# 7) overview plot for all samples (color by predicted genotype)
# =========================
all_genos_present = [g for g in sorted(df["predicted_genotype"].dropna().unique(),
                                       key=lambda x: global_genotypes.index(x) if x in global_genotypes else 999)]
fig, ax = plt.subplots(figsize=(8,6))
for g in all_genos_present:
    mask = (df["predicted_genotype"] == g)
    color = GENO_COLOR_MAP.get(g, "0.4")
    ax.scatter(df.loc[mask,"normalised mean r1"], df.loc[mask,"normalised mean r2"],
               color=color, alpha=0.85, label=g, s=30)

# overlay centroids for all centroids used (neutral small cross)
unique_centroids = sorted(set([c for lst in group_to_centroids.values() for c in lst]),
                         key=lambda x: global_genotypes.index(x) if x in global_genotypes else 999)
for cname in unique_centroids:
    cx, cy = fine_centroids[cname]
    ax.scatter(cx, cy, marker=CENTROID_MARKER, s=CENTROID_SIZE,
               color="black", linewidths=CENTROID_LINEWIDTH, alpha=0.9)

ax.set_title("All samples by predicted genotype")
scatter_common(ax)
ax.legend(title="Predicted genotype", loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "all_predicted_genotype.png"))
plt.close(fig)

print(f"[done] plots in: {OUTPUT_DIR}")
print(f"[done] enriched table: {ENRICHED_CSV}")



###################
# Define the progressive stages
stages = [
    ["αα/αα"],
    ["αα/αα", "-α3.7/αα", "-α4.2/αα"],
    ["αα/αα", "-α3.7/αα", "-α4.2/αα", "--SEA/αα"],
    sorted([g for g in df["predicted_genotype"].dropna().unique()
            if g in fine_centroids],  # only include defined centroids
           key=lambda x: list(fine_centroids.keys()).index(x))
]

stage_names = [
    "stage1_alpha_alpha_only",
    "stage2_add_3.7K_4.2K_hets",
    "stage3_add_SEA_het",
    "stage4_all_genotypes"
]

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

for stage_idx, (geno_list, name) in enumerate(zip(stages, stage_names), 1):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Plot only samples with predicted_genotype in current stage
    plotted_any = False
    for g in geno_list:
        if g not in df["predicted_genotype"].values:
            continue
        mask = df["predicted_genotype"] == g
        color = GENO_COLOR_MAP.get(g, "#888888")
        ax.scatter(
            df.loc[mask, "normalised mean r1"],
            df.loc[mask, "normalised mean r2"],
            color=color,
            alpha=0.85,
            label=g,
            s=40
        )
        plotted_any = True

    # Overlay centroids for genotypes in this stage
    for g in geno_list:
        if g in fine_centroids:
            cx, cy = fine_centroids[g]
            ax.scatter(
                cx, cy,
                marker="x",
                s=50,
                color="black",
                linewidths=1.2,
                alpha=0.9
            )
            ax.text(
                cx + 0.02, cy + 0.02, g,
                fontsize=8,
                color="black",
                alpha=0.9
            )

    if plotted_any:
        ax.set_xlim(*XLIMS)
        ax.set_ylim(*YLIMS)
        ax.set_xticks(XTICKS)
        ax.set_yticks(YTICKS)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.set_xlabel("normalised mean r1")
        ax.set_ylabel("normalised mean r2")
        ax.legend(loc="upper right", frameon=True, fontsize=8, ncol=1)

        fig.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, f"animation_{name}.png"), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"[saved] {name}")
    else:
        plt.close(fig)
        print(f"[skipped] {name} – no data")

print("[done] animation-style plots saved to:", OUTPUT_DIR)