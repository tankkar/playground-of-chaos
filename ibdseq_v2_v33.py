import pandas as pd
import matplotlib.pyplot as plt

# === 1) Load your files ===
#bed_file      = "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/IBD/temp/merged_target"
bed_file="C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/IBD/sum.bed"
#bed_file      = "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/IBD/temp/merged_errormax0.05.bed"
variants_file = "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/founder_variant20250526.tsv"

# BED has no header:
bed_df = pd.read_csv(
    bed_file,
    sep='\t',
    header=None,
    names=['chr', 'start', 'end', 'pair']
)

# Your variant TSV must have at least: cpra, HGVS, Sample
variants_df = pd.read_csv(variants_file, sep='\t')

# === 2) Normalize bed sample names to match the 'Sample' column ===
#    We take each piece before '_' in 'pair', split on '-', keep the first 8 chars.
def normalize_sample(x):
    name = x.split('-', 1)[0]      # drop the "-001-LIB1"
    return name[:8]                # keep only the 8-char code (e.g. "A0009550")

bed_df['pair'] = bed_df['pair'].apply(
    lambda p: '_'.join(normalize_sample(x) for x in p.split('_'))
)

# === 3) Build per-sample, per-chr interval map ===
intervals_map = {}
for _, row in bed_df.iterrows():
    chrom, s, e = row['chr'], row['start'], row['end']
    for sample in row['pair'].split('_'):
        intervals_map.setdefault((sample, chrom), []).append((s, e))

# === 4) Helpers to parse & merge ===
def parse_cpra(cpra):
    """ "chrX-154532269-C-A" → ("chrX", 154532269) """
    chrom, rest = cpra.split('-', 1)
    pos = int(rest.split('-', 1)[0])
    return chrom, pos

def find_merged(intervals, pos):
    """ Merge all overlapping intervals that touch `pos`. """
    merged = None
    for s, e in intervals:
        if s <= pos <= e:
            merged = [s, e]
            break
    if merged is None:
        return None, None

    changed = True
    while changed:
        changed = False
        ms, me = merged
        for s, e in intervals:
            if s <= me and e >= ms:
                if s < ms:
                    ms, changed = s, True
                if e > me:
                    me, changed = e, True
        merged = [ms, me]

    return merged

# === 5) Compute each variant’s merged IBD block and size ===
starts, ends, sizes = [], [], []
for _, row in variants_df.iterrows():
    chrom, pos = parse_cpra(row['cpra'])
    ivals = intervals_map.get((row['Sample'], chrom), [])
    ms, me = find_merged(ivals, pos)
    starts.append(ms)
    ends.append(me)
    sizes.append((me - ms) if (ms is not None and me is not None) else 0)

variants_df['start'] = starts
variants_df['end']   = ends
variants_df['size']  = sizes

# === 6) Plot one panel per CPRA using HGVS as the title ===
variants_df = variants_df[~variants_df['Sample'].isin(['A0013853', 'B0012899'])]


for cpra, grp in variants_df.groupby('cpra'):
    hgvs = grp['HGVS'].iloc[0]
    chrom, pos = parse_cpra(cpra)

    # sort descending so largest block is drawn first
    grp = grp.sort_values('size', ascending=False).reset_index(drop=True)
    samples = grp['Sample'].tolist()
    starts  = grp['start'].tolist()
    ends    = grp['end'].tolist()
    sizes   = grp['size'].tolist()

    fig, ax = plt.subplots(figsize=(8, 3))
    y = range(len(samples))

    # draw bars
    ax.barh(y, sizes, left=starts, height=0.6, color='skyblue')

    # variant positions (smaller red squares)
    ax.scatter([pos]*len(y), y,
               marker='s', s=20,
               facecolors='none',
               edgecolors='red',
               linewidths=1.2)

    # block boundaries (black squares)
    for yi, (s, e) in enumerate(zip(starts, ends)):
        if s is not None:
            ax.scatter([s, e], [yi, yi],
                       marker='s', s=30,
                       color='black')

    # size labels (e.g. "3244 kb") at the right of each bar
    x_min, x_max = ax.get_xlim()
    offset = (x_max - x_min) * 0.01
    for yi, sz in enumerate(sizes):
        if sz > 0:
            ax.text(ends[yi] + offset, yi,
                    f"{sz/1000:.0f} kb",
                    va='center', fontsize=8)

    # labels & styling
    ax.set_yticks(y)
    ax.set_yticklabels(samples)
    ax.set_xlabel('Genomic position (bp)')
    ax.set_title(hgvs)

    # move X axis up, format in Mb
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')
    ticks = ax.get_xticks()
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t/1e6:.2f} Mb" for t in ticks], fontsize=8)

    # largest at top
    ax.invert_yaxis()

    plt.tight_layout()
    plt.show()

import pandas as pd

# —————————————————————————————————————
# (A) Assume you already have variants_df with columns: cpra, start, end, size
# and that bed_df & intervals_map etc. have already been built.
# —————————————————————————————————————

# 1) Compute the shared core length per cpra
shared_records = []
for cpra, grp in variants_df.groupby('cpra'):
    # collect only real intervals
    valid = [(s, e) for s, e in zip(grp['start'], grp['end'])
             if pd.notnull(s) and pd.notnull(e)]
    if not valid:
        shared_len = 0
    else:
        shared_start = max(s for s, e in valid)
        shared_end   = min(e for s, e in valid)
        shared_len   = max(0, shared_end - shared_start)
    shared_records.append({
        'cpra':       cpra,
        'shared_len': shared_len
    })

shared_df = pd.DataFrame(shared_records)
shared_df['shared_kb'] = shared_df['shared_len'] / 1_000
shared_df['shared_mb'] = shared_df['shared_len'] / 1_000_000

# 2) Merge these back into variants_df
variants_df = variants_df.merge(
    shared_df[['cpra','shared_kb','shared_mb']],
    on='cpra',
    how='left'
)

# 3) Write out
variants_df.to_csv(
    "variants_with_shared_segment.tsv",
    sep='\t',
    index=False
)




