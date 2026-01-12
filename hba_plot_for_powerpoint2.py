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
OUTPUT_DIR = "plots2"                # all plots go here
ENRICHED_CSV = "alpha_depth_enriched.tsv"  # tab-separated enriched output

# axes & styling
XLIMS  = (-0.1, 2.5)
YLIMS  = (-0.1, 2.5)
XTICKS = np.arange(0, 2.6, 0.5)
YTICKS = np.arange(0, 2.6, 0.5)

# Original group names (used for coloring and data filtering)
GROUP_COLORS = {
    "SEA":     "#ff7f0e",
    "3.7K":    "#2ca02c",
    "4.2K":    "#d62728",
    "CONTROL": "#1f77b4",
}

# Display names for plots (biological notation)
GROUP_NAME_DISPLAY = {
    "SEA":     "--",
    "3.7K":    "-α3.7",
    "4.2K":    "-α4.2",
    "CONTROL": "CONTROL",
}

# centroid styling
CENTROID_MARKER = "x"
CENTROID_SIZE = 50
CENTROID_LINEWIDTH = 1.2
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
# Build algorithmic genotype palette
# =========================
global_genotypes = list(fine_centroids.keys())
N = max(1, len(global_genotypes))
SATURATION = 0.60
VALUE = 0.82
hues = np.linspace(0.0, 1.0, N, endpoint=False)
palette_rgb = [hsv_to_rgb((h, SATURATION, VALUE)) for h in hues]
PALETTE_HEX = [to_hex(c) for c in palette_rgb]
GENO_COLOR_MAP = {g: PALETTE_HEX[i] for i, g in enumerate(global_genotypes)}


def plot_centroids_with_offset(ax, centroid_dict, labels, base_offset=0.03):
    """
    Plot centroids with vertical offset for overlapping positions.
    """
    from collections import defaultdict

    pos_to_labels = defaultdict(list)
    for lab in labels:
        if lab in centroid_dict:
            pos = centroid_dict[lab]
            pos_key = (round(pos[0], 6), round(pos[1], 6))
            pos_to_labels[pos_key].append(lab)

    for (x, y), labs in pos_to_labels.items():
        if len(labs) == 1:
            ax.scatter(x, y, marker="x", s=CENTROID_SIZE,
                       color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
            ax.text(x + 0.02, y + 0.02, labs[0],
                    fontsize=CENTROID_TEXT_FONTSIZE,
                    color=CENTROID_TEXT_COLOR, alpha=0.9)
        else:
            for i, lab in enumerate(labs):
                dy = i * base_offset
                ax.scatter(x, y + dy, marker="x", s=CENTROID_SIZE,
                           color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
                ax.text(x + 0.02, y + dy + 0.02, lab,
                        fontsize=CENTROID_TEXT_FONTSIZE,
                        color=CENTROID_TEXT_COLOR, alpha=0.9)


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
# 5) per-group training, prediction, and plotting
# =========================
order = ["SEA","3.7K","4.2K","CONTROL"]
for grp in order:
    sub = df[df["First label"] == grp].copy()
    keys = group_to_centroids[grp]

    X_train = np.array([fine_centroids[k] for k in keys])
    y_train = np.array(keys)
    clf = NearestCentroid().fit(X_train, y_train)

    X_test = sub[["normalised mean r1","normalised mean r2"]].values
    preds = clf.predict(X_test)
    dists = pairwise_distances(X_test, clf.centroids_)
    best_idx = np.argmin(dists, axis=1)
    best_d   = dists[np.arange(len(dists)), best_idx]

    df.loc[sub.index, "predicted_genotype"]   = preds
    df.loc[sub.index, "distance_to_centroid"] = best_d

    # ---- (A) first-label scatter (one file) ----
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(sub["normalised mean r1"], sub["normalised mean r2"],
               color=GROUP_COLORS[grp], alpha=0.9)
    ax.set_title(f"{GROUP_NAME_DISPLAY[grp]} by First label")
    scatter_common(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{GROUP_NAME_DISPLAY[grp]}_first_label.png"))
    plt.close(fig)

    # ---- (B) predicted-genotype scatter (one file) ----
    genotypes_present = list(dict.fromkeys(preds))  # preserve order
    fig, ax = plt.subplots(figsize=(8,6))
    for g in genotypes_present:
        mask = (preds == g)
        color = GENO_COLOR_MAP.get(g, "0.4")
        ax.scatter(sub.loc[mask, "normalised mean r1"], sub.loc[mask, "normalised mean r2"],
                   color=color, alpha=0.9, label=g)

    for k, (cx, cy) in zip(clf.classes_, clf.centroids_):
        ax.scatter(cx, cy, marker=CENTROID_MARKER, s=CENTROID_SIZE,
                   color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
        ax.text(cx+0.02, cy+0.02, k, fontsize=CENTROID_TEXT_FONTSIZE,
                color=CENTROID_TEXT_COLOR, alpha=0.85)

    ax.set_title(f"{GROUP_NAME_DISPLAY[grp]} by predicted genotype")
    scatter_common(ax)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{GROUP_NAME_DISPLAY[grp]}_predicted_genotype.png"))
    plt.close(fig)

    # ---- (C) centroids-only scatter (one file per group) ----
    fig, ax = plt.subplots(figsize=(6,5))
    scatter_common(ax)
    for label, (cx, cy) in zip(clf.classes_, clf.centroids_):
        ax.scatter(cx, cy, marker=CENTROID_MARKER, s=CENTROID_SIZE,
                   color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)
        ax.text(cx + 0.02, cy + 0.02, label, fontsize=9,
                color=CENTROID_TEXT_COLOR, alpha=0.95)
    display_name = GROUP_NAME_DISPLAY[grp]
    ax.set_title(f"{display_name} - group centroids only")
    fig.tight_layout()
    # Use display name in filename (replace invalid chars if needed)
    safe_name = display_name.replace("/", "_").replace("\\", "_")
    fig.savefig(os.path.join(OUTPUT_DIR, f"{safe_name}_centroids_only.png"), dpi=150)
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

def count_alpha(s: str) -> int:
    if not isinstance(s, str):
        return 0
    parts = s.split("/")
    return sum(p.count("α") for p in parts)

df["copy_number"] = df["predicted_genotype"].apply(count_alpha)
df.to_csv(ENRICHED_CSV, sep="\t", index=False)

# =========================
# 7) Overview plot: all predicted genotypes
# =========================
all_genos_present = [g for g in sorted(df["predicted_genotype"].dropna().unique(),
                                       key=lambda x: global_genotypes.index(x) if x in global_genotypes else 999)]
fig, ax = plt.subplots(figsize=(8,6))
for g in all_genos_present:
    mask = (df["predicted_genotype"] == g)
    color = GENO_COLOR_MAP.get(g, "0.4")
    ax.scatter(df.loc[mask,"normalised mean r1"], df.loc[mask,"normalised mean r2"],
               color=color, alpha=0.85, label=g, s=30)

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

# =========================
# 8) Animation-style progressive plots
# =========================
EXCLUDE_GENOTYPE = "-α4.2/-α3.7"
BASELINE_GENOS = ["αα/αα", "-α4.2/αα", "-α3.7/αα", "--SEA/αα"]

all_valid_genos = [g for g in fine_centroids.keys() if g != EXCLUDE_GENOTYPE]
genotype_to_copy = {g: count_alpha(g) for g in all_valid_genos}

copy_groups = {}
for g, cn in genotype_to_copy.items():
    copy_groups.setdefault(cn, []).append(g)

stages_dict = {}
for cn in [0, 1, 2, 3, 4]:
    if cn in copy_groups:
        stages_dict[f"{cn}_copy"] = sorted(
            copy_groups[cn],
            key=lambda x: global_genotypes.index(x) if x in global_genotypes else 999
        )

max_cn = max(copy_groups.keys()) if copy_groups else 0
high_cn_genos = []
for cn in range(5, max_cn + 1):
    if cn in copy_groups:
        high_cn_genos.extend(copy_groups[cn])
if high_cn_genos:
    stages_dict["5+_copies"] = sorted(
        high_cn_genos,
        key=lambda x: global_genotypes.index(x) if x in global_genotypes else 999
    )

cumulative_genos = []
stage_names = []
stage_labels = []

for label, genos in stages_dict.items():
    filtered_genos = [g for g in genos if g != EXCLUDE_GENOTYPE]
    cumulative_genos.extend(filtered_genos)
    cumulative_genos = list(dict.fromkeys(cumulative_genos))
    stage_names.append(cumulative_genos.copy())
    stage_labels.append(label)

def format_genotype_with_copy(g):
    cn = genotype_to_copy.get(g, count_alpha(g))
    return f"{g} [{cn}-copy]"

for idx, (geno_list, label) in enumerate(zip(stage_names, stage_labels), 1):
    fig, ax = plt.subplots(figsize=(8, 6))
    plotted_any = False

    baseline_in_stage = [g for g in BASELINE_GENOS if g in geno_list and g in df["predicted_genotype"].values]
    non_baseline_in_stage = [g for g in geno_list if g not in BASELINE_GENOS and g in df["predicted_genotype"].values]

    for g in baseline_in_stage:
        mask = df["predicted_genotype"] == g
        color = GENO_COLOR_MAP.get(g, "#888888")
        ax.scatter(df.loc[mask, "normalised mean r1"], df.loc[mask, "normalised mean r2"],
                   color=color, alpha=0.75, label=format_genotype_with_copy(g), s=40)
        plotted_any = True

    for g in non_baseline_in_stage:
        mask = df["predicted_genotype"] == g
        color = GENO_COLOR_MAP.get(g, "#888888")
        ax.scatter(df.loc[mask, "normalised mean r1"], df.loc[mask, "normalised mean r2"],
                   color=color, alpha=0.85, label=format_genotype_with_copy(g), s=40)
        plotted_any = True

    from collections import defaultdict
    pos_to_genos = defaultdict(list)
    for g in geno_list:
        if g == EXCLUDE_GENOTYPE or g not in fine_centroids:
            continue
        x, y = fine_centroids[g]
        pos_key = (round(x, 6), round(y, 6))
        pos_to_genos[pos_key].append(g)

    for (x, y), _ in pos_to_genos.items():
        ax.scatter(x, y, marker=CENTROID_MARKER, s=CENTROID_SIZE,
                   color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)

    base_offset = 0.06
    for (x, y), genos_at_pos in pos_to_genos.items():
        if len(genos_at_pos) == 1:
            g = genos_at_pos[0]
            ax.text(x + 0.02, y + 0.02, format_genotype_with_copy(g),
                    fontsize=CENTROID_TEXT_FONTSIZE, color=CENTROID_TEXT_COLOR, alpha=0.9)
        else:
            for i, g in enumerate(genos_at_pos):
                dy = (i - (len(genos_at_pos) - 1) / 2) * base_offset
                ax.text(x + 0.02, y + dy + 0.02, format_genotype_with_copy(g),
                        fontsize=CENTROID_TEXT_FONTSIZE, color=CENTROID_TEXT_COLOR, alpha=0.9)

    if plotted_any:
        scatter_common(ax)
        ax.legend(loc="upper right", frameon=True, fontsize=8, ncol=1)
        fig.tight_layout()
        filename = f"animation_copy_number_{label}.png"
        fig.savefig(os.path.join(OUTPUT_DIR, filename), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"[saved] {filename}")
    else:
        plt.close(fig)
        print(f"[skipped] {label} – no data")

# =========================
# 9) Two additional requested plots
# =========================

# (A) All samples, no color (gray), no legend
fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(df["normalised mean r1"], df["normalised mean r2"], color="gray", alpha=0.7, s=30)
scatter_common(ax)
ax.set_title("All Samples (Uncolored)")
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "all_samples_uncolored.png"), dpi=300, bbox_inches='tight')
plt.close(fig)

# (B) All samples colored by 'First label' — SEA plotted LAST (on top)
# (B) All samples colored by 'First label' — with "--" (SEA) at the BASE (drawn first)
fig, ax = plt.subplots(figsize=(8, 6))

# Mapping for legend display names
label_rename = {
    "SEA": "--",
    "3.7K": "-α3.7",
    "4.2K": "-α4.2",
    "CONTROL": "CONTROL"
}

# Define draw order: "--" FIRST (base), then others
draw_order = ["SEA", "3.7K", "4.2K", "CONTROL"]
# Keep only groups present in data and with defined colors
groups_to_plot = [g for g in draw_order if g in df["First label"].values and g in GROUP_COLORS]

for group in groups_to_plot:
    subset = df[df["First label"] == group]
    ax.scatter(
        subset["normalised mean r1"],
        subset["normalised mean r2"],
        color=GROUP_COLORS[group],
        alpha=0.85,
        label=label_rename[group],  # Use renamed label
        s=40
    )

scatter_common(ax)
ax.set_title("All Samples by First Label Group")
ax.legend(title="First Label", loc="upper right")
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "all_samples_by_first_label.png"), dpi=300, bbox_inches='tight')
plt.close(fig)

# =========================
# 10) Final plot: All by predicted genotype (baseline at bottom)
# =========================
BASELINE_GENOS = ["αα/αα", "-α4.2/αα", "-α3.7/αα", "--SEA/αα"]
present_genos_unsorted = df["predicted_genotype"].dropna().unique()
all_present = [g for g in present_genos_unsorted if g in fine_centroids]
baseline_to_plot = [g for g in BASELINE_GENOS if g in all_present]
others_to_plot = [g for g in all_present if g not in BASELINE_GENOS]
others_to_plot = [g for g in global_genotypes if g in others_to_plot]
draw_order = baseline_to_plot + others_to_plot
legend_order = [g for g in global_genotypes if g in all_present]

fig, ax = plt.subplots(figsize=(9, 7))
for g in draw_order:
    mask = df["predicted_genotype"] == g
    color = GENO_COLOR_MAP.get(g, "#888888")
    alpha_val = 0.75 if g in BASELINE_GENOS else 0.85
    ax.scatter(df.loc[mask, "normalised mean r1"], df.loc[mask, "normalised mean r2"],
               color=color, alpha=alpha_val, s=35, label=g)

unique_positions = {}
for g in legend_order:
    pos = fine_centroids[g]
    unique_positions.setdefault(pos, []).append(g)

for pos in unique_positions:
    ax.scatter(pos[0], pos[1], marker=CENTROID_MARKER, s=CENTROID_SIZE,
               color="black", linewidths=CENTROID_LINEWIDTH, alpha=CENTROID_ALPHA)

from collections import defaultdict
pos_to_labels = defaultdict(list)
for g in legend_order:
    pos = fine_centroids[g]
    pos_key = (round(pos[0], 6), round(pos[1], 6))
    pos_to_labels[pos_key].append(g)

base_offset = 0.04
for (x, y), labels in pos_to_labels.items():
    if len(labels) == 1:
        ax.text(x + 0.02, y + 0.02, labels[0], fontsize=CENTROID_TEXT_FONTSIZE,
                color=CENTROID_TEXT_COLOR, alpha=0.9)
    else:
        for i, lab in enumerate(labels):
            dy = (i - (len(labels) - 1) / 2) * base_offset
            ax.text(x + 0.02, y + dy + 0.02, lab, fontsize=CENTROID_TEXT_FONTSIZE,
                    color=CENTROID_TEXT_COLOR, alpha=0.9)

scatter_common(ax)
ax.legend(handles=[
    plt.Line2D([], [], marker='o', color='w', markerfacecolor=GENO_COLOR_MAP.get(g, "#888888"),
               markersize=6, alpha=0.85, label=g)
    for g in legend_order
], title="Predicted Genotype", loc="upper right", fontsize=7, ncol=2, frameon=True)

fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, "all_samples_by_predicted_genotype_fixed_centroids.png"), dpi=300, bbox_inches='tight')
plt.close(fig)

print(f"[saved] all_samples_by_predicted_genotype_fixed_centroids.png")