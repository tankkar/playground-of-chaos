import pandas as pd

# Read the TSV files
freq_df = pd.read_csv('final_merged.bed', sep='\t', 
                      names=['chrom', 'start', 'end', 'internal_freq', 'sample_id', 'variant_type'])

sv_df = pd.read_csv('merged_sv_carrier_screening.tsv', sep='\t')

# Create matching keys for both dataframes
freq_df['match_key'] = freq_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)
sv_df['match_key'] = sv_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)


freq_df['start'] = freq_df['start'].astype(int)
freq_df['end'] = freq_df['end'].astype(int)
sv_df['start'] = sv_df['start'].astype(int)
sv_df['end'] = sv_df['end'].astype(float).astype(int)  # if end has decimals

# Let's print some sample keys to debug
freq_df['match_key'] = freq_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)
sv_df['match_key'] = sv_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)


# Merge on matching key
merged_df = sv_df.merge(freq_df[['match_key', 'internal_freq']], 
                       on='match_key', 
                       how='left')

# Drop the matching key
merged_df = merged_df.drop('match_key', axis=1)
merged_df.to_csv('merged_output.tsv', sep='\t', index=False)

TOTAL_SAMPLES = 18261
TOTAL_ALLELES = 2 * TOTAL_SAMPLES  # 36522

# 1. Calculate allele frequency
merged_df["allele_frequency"] = merged_df["internal_freq"] / TOTAL_ALLELES

# 2. Classify variant as rare (≤ 2%)
merged_df["is_rare"] = merged_df["allele_frequency"] <= 0.01

# Optionally, if you want a text label ("Rare" or "Not Rare")
merged_df["rare_label"] = merged_df["is_rare"].apply(lambda x: "Rare" if x else "Not Rare")

# Now merged_df has two new columns:
# "allele_frequency" and "is_rare" (plus optionally "rare_label").
# E.g. you could write out the result:
merged_df.to_csv("merged_with_allelefreq.txt", sep="\t", index=False)

















# Convert datatypes to ensure consistency
freq_df['start'] = freq_df['start'].astype(int)
freq_df['end'] = freq_df['end'].astype(int)
sv_df['start'] = sv_df['start'].astype(int)
sv_df['end'] = sv_df['end'].astype(float).astype(int)  # if end has decimals

# Let's print some sample keys to debug
freq_df['match_key'] = freq_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)
sv_df['match_key'] = sv_df.apply(lambda x: f"{x['chrom']}_{x['start']}_{x['end']}_{x['sample_id']}", axis=1)

print("Sample freq_df keys:")
print(freq_df['match_key'].head())
print("\nSample sv_df keys:")
print(sv_df['match_key'].head())

# Let's also check if any keys match at all
common_keys = set(freq_df['match_key']).intersection(set(sv_df['match_key']))
print("\nNumber of matching keys:", len(common_keys))
if len(common_keys) > 0:
    print("Sample matching key:", list(common_keys)[0])