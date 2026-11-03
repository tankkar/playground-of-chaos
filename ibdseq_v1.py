import pandas as pd

# Load IBD bed file
bed_df = pd.read_csv(
    "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/IBD/sum.bed",
    sep='\t', header=None,
    names=['chr', 'start', 'end', 'pair']
)

# Build per-sample, per-chromosome interval list
intervals_map = {}
for _, row in bed_df.iterrows():
    chrom = row['chr']
    start, end = row['start'], row['end']
    for sample in row['pair'].split('_'):
        intervals_map.setdefault((sample, chrom), []).append((start, end))

# Read variants
variants_df = pd.read_csv("founder_variant20250526.tsv", sep='\t')

def parse_cpra(cpra):
    parts = cpra.split('-')
    chrom = parts[0]
    pos = int(parts[1])
    return chrom, pos

def find_merged_region(intervals, pos):
    # Find intervals connected to variant pos
    # Initialize with any interval that contains pos
    merged = None
    for (s, e) in intervals:
        if s <= pos <= e:
            merged = [s, e]
            break
    if merged is None:
        return None, None  # no region covers variant
    
    changed = True
    while changed:
        changed = False
        ms, me = merged
        for (s, e) in intervals:
            if s <= me and e >= ms:
                if s < ms:
                    ms = s
                    changed = True
                if e > me:
                    me = e
                    changed = True
        merged = [ms, me]
    return merged

# Compute merged IBD region and size for each variant
merged_starts = []
merged_ends = []
merged_sizes = []
for _, row in variants_df.iterrows():
    chrom, pos = parse_cpra(row['cpra'])
    intervals = intervals_map.get((row['Sample'], chrom), [])
    ms, me = find_merged_region(intervals, pos)
    if ms is None:
        merged_starts.append(None)
        merged_ends.append(None)
        merged_sizes.append(0)
    else:
        merged_starts.append(ms)
        merged_ends.append(me)
        merged_sizes.append(me - ms)

variants_df['IBD_merged_start'] = merged_starts
variants_df['IBD_merged_end'] = merged_ends
variants_df['IBD_merged_size'] = merged_sizes


variants_df.to_csv('temp.csv')