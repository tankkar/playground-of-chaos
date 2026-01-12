import os
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestCentroid
from sklearn.metrics import pairwise_distances
import matplotlib.pyplot as plt

# ─── 0) Prepare output directory ─────────────────────────────────────────────
os.makedirs("plots", exist_ok=True)

# ─── 1) Load data ─────────────────────────────────────────────────────────────
#df = pd.read_excel('200bp_new_run_v2.xlsx', sheet_name='200bp_new_run')
df = pd.read_csv('200bp_r2_fixed.csv')
#df = pd.read_csv("HBA_Validation_cohort_result.csv")
# ─── 2) Filter data ────────────────────────────────────────────────────────────
df = df[df['Median Depth QC Status'] == "Pass"]

# ─── 3) Define regions ─────────────────────────────────────────────────────────
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

# ─── 4) Calculate means ─────────────────────────────────────────────────────────
df['mean_r1'] = df[region1_cols].mean(axis=1)
df['mean_r2'] = df[region2_cols].mean(axis=1)

# ─── 5) Prepare output columns ─────────────────────────────────────────────────
df['predicted_genotype']   = np.nan
df['distance_to_centroid'] = np.nan

# ─── 6) Centroid definitions ───────────────────────────────────────────────────
fine_centroids = {
    'αα/αα':         (1.0, 1.0),
    'αα/ααα3.7':     (1.0, 1.5),
    'αα/ααα4.2':     (1.5, 1.0),
    'ααα3.7/ααα3.7': (1.0, 2.0),
    'ααα4.2/ααα4.2': (2.0, 1.0),
    '--SEA/--SEA':   (0.0, 0.0),
    '--SEA/αα':      (0.5, 0.5),
    '--SEA/-α3.7':   (0.5, 0.0),
    '--SEA/-α4.2':   (0.0, 0.5),
    '--SEA/ααα3.7':  (0.5, 1.0),
    '--SEA/ααα4.2':  (1.0, 0.5),
    '--SEA/αα4.2α3.7': (1.0, 0),
    '-α4.2/αα':      (0.5, 1.0),
    '-α4.2/-α4.2':   (0.0, 1.0),
    '-α4.2/-α3.7':   (0.5, 0.5),
    '-α4.2/ααα3.7':  (0.5, 1.5),
    '-α3.7/αα':      (1.0, 0.5),
    '-α3.7/-α3.7':   (1.0, 0.0),
    '-α3.7/-α4.2':   (0.5, 0.5),
    '-α3.7/ααα4.2':  (1.5, 0.5),
}

# ─── 7) Group definitions ──────────────────────────────────────────────────────
group_to_centroids = {
    'SEA':     ['--SEA/--SEA','--SEA/αα','--SEA/-α3.7','--SEA/-α4.2','--SEA/ααα3.7','--SEA/ααα4.2', '--SEA/αα4.2α3.7'],
    '3.7K':    ['-α3.7/αα','-α3.7/-α3.7','-α3.7/-α4.2','-α3.7/ααα4.2'],
    '4.2K':    ['-α4.2/αα','-α4.2/-α4.2','-α4.2/ααα3.7'],
    'CONTROL':['αα/αα','αα/ααα3.7','αα/ααα4.2','ααα3.7/ααα3.7','ααα4.2/ααα4.2'],
}

# ─── 8) Plotting parameters ────────────────────────────────────────────────────
first_label_colors = {'SEA':'#ff7f0e','3.7K':'#2ca02c','4.2K':'#d62728','CONTROL':'#1f77b4'}
xlims   = (-0.1,2)
ylims   = (-0.1,2.5)
xticks  = np.arange(0,2.1,0.5)
yticks  = np.arange(0,2.6,0.5)

# ─── 9) Main analysis & saving plots ────────────────────────────────────────────
for grp in ['SEA','3.7K','4.2K','CONTROL']:
    sub  = df[df['First label']==grp].copy()
    keys = group_to_centroids[grp]

    # train classifier
    X_train = np.array([fine_centroids[k] for k in keys])
    y_train = np.array(keys)
    clf     = NearestCentroid().fit(X_train, y_train)

    # predict + distances
    X_test   = sub[['mean_r1','mean_r2']].values
    preds    = clf.predict(X_test)
    dists    = pairwise_distances(X_test, clf.centroids_)
    best_idx = np.argmin(dists, axis=1)
    best_d   = dists[np.arange(len(dists)), best_idx]

    # write back
    df.loc[sub.index,'predicted_genotype']   = preds
    df.loc[sub.index,'distance_to_centroid'] = best_d

    # first‐label plot
    plt.figure(figsize=(8,6))
    plt.scatter(sub['mean_r1'], sub['mean_r2'],
                color=first_label_colors[grp], alpha=0.9)
    plt.title(f'{grp} by First label')
    plt.xlim(*xlims); plt.ylim(*ylims)
    plt.xticks(xticks); plt.yticks(yticks)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'plots/{grp}_first_label.png')
    plt.close()

    # predicted‐genotype plot
    genotypes       = list(dict.fromkeys(preds))
    cmap_group      = plt.get_cmap('tab20', len(genotypes))
    genotype_colors = {g:cmap_group(i) for i,g in enumerate(genotypes)}

    plt.figure(figsize=(8,6))
    for g in genotypes:
        mask = (preds==g)
        plt.scatter(sub.loc[mask,'mean_r1'], sub.loc[mask,'mean_r2'],
                    color=genotype_colors[g], alpha=0.9, label=g)
    for k,(cx,cy) in zip(clf.classes_, clf.centroids_):
        plt.scatter(cx, cy, marker='X', s=100, color='black', alpha=0.3)
        plt.text(cx+0.02, cy+0.02, k, fontsize=8, alpha=0.8)

    plt.title(f'{grp} by predicted genotype')
    plt.xlim(*xlims); plt.ylim(*ylims)
    plt.xticks(xticks); plt.yticks(yticks)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(frameon=False, loc='upper right')
    plt.tight_layout()
    plt.savefig(f'plots/{grp}_predicted_genotype.png')
    plt.close()

# ─── 10) Map to human‐readable column ───────────────────────────────────────────
descriptive_map = {
    '--SEA/--SEA':'SEA hom del','--SEA/αα':'SEA','--SEA/-α3.7':'SEA 3.7K','--SEA/-α4.2':'SEA 4.2K',
    '--SEA/ααα3.7':'SEA + 3.7 dup','--SEA/ααα4.2':'SEA + 4.2 dup', '--SEA/αα4.2α3.7':'complex',
    '-α3.7/-α3.7':'3.7K hom del','-α3.7/αα':'3.7K','-α3.7/-α4.2':'3.7+4.2 del','-α3.7/ααα4.2':'3.7 del+4.2 dup',
    '-α4.2/-α4.2':'4.2K hom del','-α4.2/αα':'4.2K','-α4.2/ααα3.7':'4.2 del+3.7 dup',
    'αα/αα':'CONTROL','αα/ααα3.7':'3.7 dup','αα/ααα4.2':'4.2 dup',
    'ααα3.7/ααα3.7':'3.7 triplication','ααα4.2/ααα4.2':'4.2 triplication',
}
df['translated_genotype'] = df['predicted_genotype'].map(descriptive_map).fillna(df['predicted_genotype'])

# ─── 11) Combined plot for all samples ─────────────────────────────────────────
all_genos = sorted(df['predicted_genotype'].unique())
cmap_all  = plt.get_cmap('tab20', len(all_genos))
geno_cols = {g:cmap_all(i) for i,g in enumerate(all_genos)}

plt.figure(figsize=(8,6))
for g in all_genos:
    mask = df['predicted_genotype']==g
    plt.scatter(df.loc[mask,'mean_r1'], df.loc[mask,'mean_r2'],
                color=geno_cols[g], label=g, alpha=0.8)

plt.xlim(*xlims); plt.ylim(*ylims)
plt.xticks(xticks); plt.yticks(yticks)
plt.xlabel('mean_r1'); plt.ylabel('mean_r2')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(title='Predicted genotype', bbox_to_anchor=(1.05,1), loc='upper left')
plt.title('All samples by predicted genotype')
plt.tight_layout()
plt.savefig('plots/all_predicted_genotype.png')
plt.close()


# 11) Define your human‑readable map
descriptive_map = {
    '--SEA/--SEA':   'SEA hom del',
    '--SEA/αα':      'SEA',
    '--SEA/-α3.7':   'SEA 3.7K',
    '--SEA/-α4.2':   'SEA 4.2K',
    '--SEA/ααα3.7':  'SEA + 3.7 dup',
    '--SEA/ααα4.2':  'SEA + 4.2 dup',
    '--SEA/αα4.2α3.7': 'SEA + 4.2dup + 3.7del',
    '-α3.7/-α3.7':   '3.7K hom del',
    '-α3.7/αα':      '3.7K',
    '-α3.7/-α4.2':   '3.7+4.2 del',
    '-α3.7/ααα4.2':  '3.7 del+4.2 dup',

    '-α4.2/-α4.2':   '4.2K hom del',
    '-α4.2/αα':      '4.2K',
    '-α4.2/ααα3.7':  '4.2 del+3.7 dup',

    'αα/αα':         'CONTROL',
    'αα/ααα3.7':     '3.7 dup',
    'αα/ααα4.2':     '4.2 dup',
    'ααα3.7/ααα3.7': '3.7 triplication',
    'ααα4.2/ααα4.2': '4.2 triplication',
}

df['translated_genotype'] = df['predicted_genotype'].map(descriptive_map)


# 13) Simplify to pure ASCII: α→a, drop '-'  
df['simple_genotype'] = (
    df['predicted_genotype']
      .str.replace('α', 'a', regex=False)
      .str.replace('-',  '', regex=False)
)

df['copy_number'] = (
    df['predicted_genotype']
      .str.split('/')                              # [hap1, hap2]
      .apply(lambda parts: sum(p.count('α') for p in parts))
)

df.to_csv('temp_20250926.csv')
# B) Prepare a color map over the distinct copy numbers
unique_cn = sorted(df['copy_number'].unique())
cmap_cn   = plt.get_cmap('tab10', len(unique_cn))
cn_colors = {cn: cmap_cn(i) for i, cn in enumerate(unique_cn)}

# C) Plot all samples, color by copy number
plt.figure(figsize=(8,6))
for cn in unique_cn:
    mask = df['copy_number'] == cn
    plt.scatter(
        df.loc[mask, 'mean_r1'],
        df.loc[mask, 'mean_r2'],
        color=cn_colors[cn],
        label=f'CN={cn}',
        alpha=0.8
    )

plt.xlim(*xlims); plt.ylim(*ylims)
plt.xticks(xticks); plt.yticks(yticks)
plt.xlabel('mean_r1'); plt.ylabel('mean_r2')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(title='Copy number', bbox_to_anchor=(1.05,1), loc='upper left')
plt.title('All samples by total α‑copy number')
plt.tight_layout()
plt.savefig('plots/all_by_copy_number.png')
plt.close()





######plot empty grid#####
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ─── 1) Define Plotting Constants ───────────────────────────────────────
xlims = (-0.1, 2)
ylims = (-0.1, 2.5)
xticks = np.arange(0, 2.1, 0.5)
yticks = np.arange(0, 2.6, 0.5)

group_colors = {
    'SEA':     '#ff7f0e',
    '3.7K':    '#2ca02c',
    '4.2K':    '#d62728',
    'CONTROL': '#1f77b4'
}

# ─── 2) Create Faceted Plot ─────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

group_to_axis = {
    'SEA':     0,
    '3.7K':    1,
    '4.2K':    2,
    'CONTROL': 3
}

# Plot centroids
for group in ['SEA', '3.7K', '4.2K', 'CONTROL']:
    ax = axes[group_to_axis[group]]
    keys = group_to_centroids[group]
    color = group_colors[group]
    
    for genotype in keys:
        x, y = fine_centroids[genotype]
        ax.scatter(x, y, color=color, marker='X', s=100, edgecolor='black', alpha=0.8)
        ax.text(x + 0.02, y + 0.02, genotype, fontsize=8, alpha=0.8)

    # No title
    ax.set_xlabel('mean_r1')
    ax.set_ylabel('mean_r2')
    ax.set_xlim(*xlims)
    ax.set_ylim(*ylims)
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.grid(True, linestyle='--', alpha=0.6)

# ─── 3) Add Shared Legend ───────────────────────────────────────────────
legend_elements = [
    Line2D([0], [0], marker='X', color='w', label=group,
           markerfacecolor=group_colors[group], markersize=10, linestyle='')
    for group in ['SEA', '3.7K', '4.2K', 'CONTROL']
]

fig.legend(handles=legend_elements, title='Genotype Group', 
            loc='upper right', bbox_to_anchor=(1.15, 0.9))

# ─── 4) Final Formatting & Export ───────────────────────────────────────
plt.tight_layout()
plt.savefig('plots/faceted_centroids_no_title.svg', format='svg', bbox_inches='tight')
plt.close()


# ─── Plot all samples in a single diagram (no centroids, no color by group) ───
plt.figure(figsize=(8, 6))
plt.scatter(df['mean_r1'], df['mean_r2'], color='gray', alpha=0.7, s=30)

plt.xlim(*xlims)
plt.ylim(*ylims)
plt.xticks(xticks)
plt.yticks(yticks)
plt.xlabel('mean_r1')
plt.ylabel('mean_r2')
plt.title('All samples (no grouping)')
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig('plots/all_samples_plain.png', dpi=300)
plt.close()