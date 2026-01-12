import os
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestCentroid
from sklearn.metrics import pairwise_distances
import matplotlib
matplotlib.use("Agg")  # safe in headless envs
import matplotlib.pyplot as plt

# =========================
# 0) user-config
# =========================
INPUT_CSV  = "200bp_r2_fixed.csv"   # change if needed
OUTPUT_DIR = "plots"                 # all plots go here
ENRICHED_CSV = "alpha_depth_enriched.tsv"  # tab-separated enriched output

# axes & styling
XLIMS  = (-0.1, 2.0)
YLIMS  = (-0.1, 2.5)
XTICKS = np.arange(0, 2.1, 0.5)
YTICKS = np.arange(0, 2.6, 0.5)

GROUP_COLORS = {
    "SEA":     "#ff7f0e",
    "3.7K":    "#2ca02c",
    "4.2K":    "#d62728",
    "CONTROL": "#1f77b4",
}

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
    genotypes = list(dict.fromkeys(preds))  # preserve order
    cmap = plt.get_cmap("tab20", len(genotypes))
    geno_colors = {g: cmap(i) for i, g in enumerate(genotypes)}

    fig, ax = plt.subplots(figsize=(8,6))
    for g in genotypes:
        mask = (preds == g)
        ax.scatter(
            sub.loc[mask, "normalised mean r1"], sub.loc[mask, "normalised mean r2"],
            color=geno_colors[g], alpha=0.9, label=g
        )

    # overlay centroids for that group
    for k, (cx, cy) in zip(clf.classes_, clf.centroids_):
        ax.scatter(cx, cy, marker="X", s=110, color="black", alpha=0.35)
        ax.text(cx+0.02, cy+0.02, k, fontsize=8, alpha=0.85)

    ax.set_title(f"{grp} by predicted genotype")
    scatter_common(ax)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{grp}_predicted_genotype.png"))
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
# 7) optional: overview plot for all samples (color by predicted genotype)
# =========================
all_genos = [g for g in sorted(df["predicted_genotype"].dropna().unique())]
cmap_all  = plt.get_cmap("tab20", len(all_genos))
geno_cols = {g: cmap_all(i) for i, g in enumerate(all_genos)}

fig, ax = plt.subplots(figsize=(8,6))
for g in all_genos:
    mask = (df["predicted_genotype"] == g)
    ax.scatter(df.loc[mask,"normalised mean r1"], df.loc[mask,"normalised mean r2"],
               color=geno_cols[g], alpha=0.8, label=g)

ax.set_title("All samples by predicted genotype")
scatter_common(ax)
ax.legend(title="Predicted genotype", loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "all_predicted_genotype.png"))
plt.close(fig)

print(f"[done] plots in: {OUTPUT_DIR}")
print(f"[done] enriched table: {ENRICHED_CSV}")
