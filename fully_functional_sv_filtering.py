#new parsing
import pandas as pd
import io
import os
import gzip
import numpy as np

def find_genes_for_sv(sv_df):
    refseq_df = pd.read_csv("C:/Users/dlhyeung/Downloads/refseq_denis.tsv", sep='\t')
    sv_df['gene_symbols'] = pd.NA
    sv_df['mane_selects'] = pd.NA

    for sv_index, sv in sv_df.iterrows():
        matching_genes = refseq_df[(refseq_df['chrom'] == sv['chrom']) &
                                   (refseq_df['txStart'] <= sv['end']) &
                                   (refseq_df['txEnd'] >= sv['start'])]
        if not matching_genes.empty:
            sv_df.at[sv_index, 'gene_symbols'] = ','.join(matching_genes['gene_symbol'].unique())
            sv_df.at[sv_index, 'mane_selects'] = ','.join(matching_genes['name'].unique())
    #sv_df.drop(columns='gene_symbol')
    sv_df.rename(columns={'gene_symbol':'gene_symbols'}, inplace = True)
    return sv_df

def parse_refseq_for_boundaries_corrected(refseq_file):
    refseq_df = pd.read_csv(refseq_file, sep='\t',
                            converters={'chrom': str, 'exonStarts': lambda x: x.strip(','),
                                        'exonEnds': lambda x: x.strip(',')})
    refseq_df.columns = [col.strip() for col in refseq_df.columns]
    parsed_data = []

    for _, row in refseq_df.iterrows():
        gene_data = {
            'chrom': row['chrom'],
            'gene_symbol': row['gene_symbol'],
            'strand': row['strand']  # Include 'strand' information
        }
        exon_starts = list(map(int, row['exonStarts'].split(',')))
        exon_ends = list(map(int, row['exonEnds'].split(',')))

        # For genes on the '+' strand
        if row['strand'] == '+':
            gene_data['5\'utr_region'] = f"{row['txStart']}-{exon_starts[0]}"
            exons = list(zip(exon_starts, exon_ends))
        # For genes on the '-' strand, no reversal of exons order
        else:
            gene_data['5\'utr_region'] = f"{exon_ends[-1]}-{row['txEnd']}"
            exons = list(zip(exon_starts, exon_ends))

        for i, (start, end) in enumerate(exons, 1):
            gene_data[f'exon{i}'] = f'{start}-{end}'

        introns = []
        for i in range(len(exons) - 1):
            start = exons[i][1]
            end = exons[i + 1][0]
            introns.append((start, end))

        for i, (start, end) in enumerate(introns, 1):
            gene_data[f'intron{i}'] = f'{start}-{end}'

        parsed_data.append(gene_data)

    parsed_df = pd.DataFrame(parsed_data)
    return parsed_df

def preprocess_refseq_df(refseq_df):
    if strand == '-':
            exon_starts = exon_starts[::-1]
            exon_ends = exon_ends[::-1]
    for col in refseq_df.columns:
        if 'exon' in col or 'intron' in col or col == "5'utr_region":
            refseq_df[col] = refseq_df[col].astype(str)
    return refseq_df

def annotate_sv_with_gene_feature(sv_df, refseq_df):
    # Initializing new columns for annotations
    sv_df['breakend1_pos'] = 'Outside gene'
    sv_df['breakend2_pos'] = 'Outside gene'

    # Iterate over SVs
    for sv_index, sv in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv['chrom'], sv['start'], sv['end']
        genes_overlapped = sv['gene_symbols']

        # Check if gene_symbols is NA or contains multiple genes
        if pd.isna(genes_overlapped) or ',' in str(genes_overlapped):
            continue

        # Ensure only SVs that overlap with a single gene are processed
        gene_data = refseq_df[(refseq_df['chrom'] == chrom_sv) & (refseq_df['gene_symbol'] == genes_overlapped)].iloc[0]

        # Check each gene feature (exon or intron) for overlap
        for feature in gene_data.index:
            if 'exon' in feature or 'intron' in feature or "5'utr" in feature:
                feature_range_str = gene_data[feature]
                if pd.isna(feature_range_str) or '-' not in str(feature_range_str):
                    continue  # Skip if feature range is NA or improperly formatted
                start_feature, end_feature = map(int, str(feature_range_str).split('-'))

                # Check overlaps for SV start (breakend1) and end (breakend2)
                if start_sv >= start_feature and start_sv <= end_feature:
                    sv_df.at[sv_index, 'breakend1_pos'] = f"{genes_overlapped}:{feature}"
                if end_sv >= start_feature and end_sv <= end_feature:
                    sv_df.at[sv_index, 'breakend2_pos'] = f"{genes_overlapped}:{feature}"

    return sv_df

def annotate_sv_positions(sv_df, refseq_df):
    # Initialize columns for annotations
    sv_df['breakend1_pos'] = 'NA'
    sv_df['breakend2_pos'] = 'NA'
    
    # Iterate through each SV
    for sv_index, sv_row in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv_row['chrom'], sv_row['start'], sv_row['end']
        gene_symbol = sv_row['gene_symbols']
        
        # Skip if multiple genes are matched
        if ',' in str(gene_symbol):
            continue
        
        # Filter for the corresponding gene in refseq_df
        gene_row = refseq_df[refseq_df['gene_symbol'] == gene_symbol].iloc[0]
        
        def find_feature_position(pos, gene_row):
            # Iterate through each feature column to find where the position falls
            for feature in gene_row.index:
                if 'exon' in feature or 'intron' in feature or "5'utr" in feature:
                    feature_range = str(gene_row[feature])
                    if '-' in feature_range:
                        start_feature, end_feature = map(int, feature_range.split('-'))
                        if start_feature <= pos <= end_feature:
                            return f"{gene_symbol}:{feature}"
            return 'NA'
        
        # Annotate start and end positions
        sv_df.at[sv_index, 'breakend1_pos'] = find_feature_position(start_sv, gene_row)
        sv_df.at[sv_index, 'breakend2_pos'] = find_feature_position(end_sv, gene_row)
    
    return sv_df

def annotate_sv_positions_debug(sv_df, refseq_df):
    sv_df['breakend1_pos'] = 'NA'
    sv_df['breakend2_pos'] = 'NA'
    
    for sv_index, sv_row in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv_row['chrom'], sv_row['start'], sv_row['end']
        gene_symbol = sv_row['gene_symbols']
        
        if ',' in str(gene_symbol) or pd.isna(gene_symbol):
            print(f"Skipping SV due to multiple or no gene_symbols: {gene_symbol}")
            continue

        gene_matches = refseq_df[(refseq_df['gene_symbol'] == gene_symbol) & (refseq_df['chrom'] == chrom_sv)]
        if gene_matches.empty:
            print(f"No matching gene found in refseq_df for gene_symbol: {gene_symbol} on chrom: {chrom_sv}")
            continue

        gene_data = gene_matches.iloc[0]
        feature_found = False
        for feature in gene_data.index:
            if 'exon' in feature or 'intron' in feature or "5'utr" in feature:
                feature_range_str = gene_data[feature]
                if pd.isna(feature_range_str) or '-' not in str(feature_range_str):
                    continue  # Skip if feature range is NA or improperly formatted
                start_feature, end_feature = map(int, str(feature_range_str).split('-'))
                # Check overlaps for SV start (breakend1) and end (breakend2)
                if start_sv >= start_feature and start_sv <= end_feature:
                    sv_df.at[sv_index, 'breakend1_pos'] = f"{gene_symbol}:{feature}"
                    feature_found = True
                if end_sv >= start_feature and end_sv <= end_feature:
                    sv_df.at[sv_index, 'breakend2_pos'] = f"{gene_symbol}:{feature}"
                    feature_found = True

        if not feature_found:
            print(f"Feature not found for SV: {start_sv}-{end_sv}, Gene: {gene_symbol}")
    
    return sv_df


def annotate_sv_with_additional_info(sv_df, refseq_df):
    # Initialize new columns
    sv_df['num_exons_affected'] = 0
    sv_df['num_genes_affected'] = 0

    for index, sv in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv['chrom'], sv['start'], sv['end']
        genes_overlapped = sv['gene_symbols']

        # Calculate number of genes affected
        if not pd.isna(genes_overlapped):
            sv_df.at[index, 'num_genes_affected'] = len(genes_overlapped.split(','))

        # Process only SVs that overlap with a single gene for exon count
        if sv_df.at[index, 'num_genes_affected'] == 1:
            gene_data = refseq_df[(refseq_df['chrom'] == chrom_sv) & (refseq_df['gene_symbol'] == genes_overlapped)].iloc[0]
            exons_affected = set()

            # Check each gene feature (exon) for overlap
            for feature in gene_data.index:
                if 'exon' in feature:
                    feature_range_str = gene_data[feature]
                    if pd.isna(feature_range_str) or '-' not in str(feature_range_str):
                        continue  # Skip if feature range is NA or improperly formatted
                    start_feature, end_feature = map(int, str(feature_range_str).split('-'))
                    # Check if SV overlaps with the exon
                    if (start_sv <= end_feature and end_sv >= start_feature):
                        exons_affected.add(feature)

            sv_df.at[index, 'num_exons_affected'] = len(exons_affected)

    return sv_df

def preprocess_sv_df(sv_df):
    def extract_end(info_str):
        for field in info_str.split(";"):
            if field.startswith("END="):
                return int(field.replace("END=", ""))
        return None
    sv_df = sv_df[sv_df['INFO'].str.startswith('PRECISE') | sv_df['INFO'].str.startswith('IMPRECISE')]
    sv_df['end'] = sv_df['INFO'].apply(extract_end)
    sv_df = sv_df.rename(columns={'CHROM': 'chrom', 'POS': 'start'})
    sv_df = sv_df[['chrom', 'start', 'end', 'INFO']]

    return sv_df

# Example usage
#sv_bed_path = "C:/Users/dlhyeung/Downloads/processed_filtered.sv.vcf.gz"

def read_vcf(path):
    # Use gzip.open for .gz files
    open_func = gzip.open if path.endswith('.gz') else open
    with open_func(path, 'rt') as f:  # Note the 'rt' mode for reading text
        lines = [l for l in f if not l.startswith('##')]
    return pd.read_csv(
        io.StringIO(''.join(lines)),
        dtype={'#CHROM': str, 'POS': int, 'ID': str, 'REF': str, 'ALT': str,
               'QUAL': str, 'FILTER': str, 'INFO': str},
        sep='\t'
    ).rename(columns={'#CHROM': 'CHROM'})

def extract_svlen_abs(info):
    for part in info.split(';'):
        if part.startswith('SVLEN='):
            try:
                return abs(int(part.split('=')[1]))
            except ValueError:  # Handle cases where SVLEN cannot be converted to int
                return np.nan
    return np.nan


sv_path = "C:/Users/dlhyeung/Downloads/test.sv.vcf.gz"
sv_df = read_vcf(sv_path)
sv_df = preprocess_sv_df(sv_df)

refseq_csv_path = 'C:/Users/dlhyeung/Downloads/refseq_denis.tsv'
refseq_df = parse_refseq_for_boundaries_corrected(refseq_csv_path)

# Annotate SVs with gene symbols, mane selects, and gene features
sv_df = find_genes_for_sv(sv_df)  
sv_df = annotate_sv_positions_debug(sv_df, refseq_df)
sv_df = annotate_sv_with_additional_info(sv_df, refseq_df)
sv_df['SVLEN_ABS'] = sv_df['INFO'].apply(extract_svlen_abs)


# Correct num_exons_affected for SVs affecting more than one gene
sv_df.loc[sv_df['num_genes_affected'] > 1, 'num_exons_affected'] = np.NaN


# Apply final filtering criteria
# 1. Remove SVs where num_exons_affected is explicitly zero
# 2. For SVs where num_genes_affected is 2, keep only those with an absolute SV length >= 2000 or with valid breakend positions
final_filtered_sv_df = sv_df[~((sv_df['num_exons_affected'] == 0) & (sv_df['num_genes_affected'] != 2))]
final_filtered_sv_df = final_filtered_sv_df[
    ~(
        (final_filtered_sv_df['num_genes_affected'] == 2) &
        (final_filtered_sv_df['breakend1_pos'] == 'NA') &
        (final_filtered_sv_df['breakend2_pos'] == 'NA') &
        (final_filtered_sv_df['SVLEN_ABS'] < 2000)
    )
]

# Drop the temporary SVLEN_ABS column as it's no longer needed
final_filtered_sv_df = final_filtered_sv_df.drop(columns=['SVLEN_ABS'])

# Save the filtered data
final_filtered_sv_df.to_csv('final_filtered.csv', index=False)

# Output to inspect
print(final_filtered_sv_df.head())


#Extend with morbid annotation
column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
morbid_map = pd.read_csv("C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/morbidmap.txt", sep='\t', names=column_names, header=None)

morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]

valid_morbid_genes = set()
for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
    valid_morbid_genes.update(gene.strip() for gene in genes)

# Since gene_symbols in final_filtered_sv_df can contain multiple genes separated by commas,
# we need to check each gene in the list of gene symbols against the morbid gene set.
def check_morbid_gene(gene_symbols):
    # Split gene_symbols string into a list of individual genes
    genes = gene_symbols.split(',')
    # Check if any of the genes are in the valid_morbid_genes set
    morbid_genes = [gene for gene in genes if gene.strip() in valid_morbid_genes]
    # Return 'Yes' if there are any morbid genes; otherwise, 'No'
    return 'Yes' if morbid_genes else 'No'

# Apply the function to the 'gene_symbols' column
final_filtered_sv_df['Morbid Gene'] = final_filtered_sv_df['gene_symbols'].apply(check_morbid_gene)

# Example of how to view the DataFrame with the new 'Morbid Gene' column
print(final_filtered_sv_df[['gene_symbols', 'Morbid Gene']].head())