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
            'strand': row['strand'],
            'exonCount': row['exonCount']  
        }
        exon_starts = list(map(int, row['exonStarts'].split(',')))
        exon_ends = list(map(int, row['exonEnds'].split(',')))
        if row['strand'] == '+':
            gene_data['5\'utr_region'] = f"{row['txStart']}-{exon_starts[0]}"
            exons = list(zip(exon_starts, exon_ends))
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

def reverse_exon_intron_order(refseq_df):
    corrected_data = []
    for _, row in refseq_df.iterrows():
        gene_data = row.to_dict()  
        if row['strand'] == '-':
            exon_columns = [f'exon{i}' for i in range(1, int(row['exonCount']) + 1)]
            intron_columns = [f'intron{i}' for i in range(1, int(row['exonCount']))]  
            reversed_exons = {f'exon{i}': gene_data[col] for i, col in enumerate(reversed(exon_columns), 1)}
            reversed_introns = {f'intron{i}': gene_data[col] for i, col in enumerate(reversed(intron_columns), 1) if col in gene_data}
            gene_data.update(reversed_exons)
            gene_data.update(reversed_introns)
        corrected_data.append(gene_data)
    return pd.DataFrame(corrected_data)

def annotate_sv_positions(sv_df, refseq_df):
    sv_df['breakend1_pos'] = 'Outside Gene'
    sv_df['breakend2_pos'] = 'Outside Gene'
    
    for sv_index, sv_row in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv_row['chrom'], sv_row['start'], sv_row['end']
        gene_symbol = sv_row['gene_symbols']
        gene_row = refseq_df[(refseq_df['gene_symbol'] == gene_symbol) & (refseq_df['chrom'] == chrom_sv)]
        
        if gene_row.empty or ',' in str(gene_symbol):
            continue  

        gene_row = gene_row.iloc[0]
        strand = gene_row['strand']

        def find_feature_position(pos, gene_row, strand):
            features = [col for col in gene_row.index if 'exon' in col or 'intron' in col or "5'utr" in col]
            if strand == '-':
                features = features[::-1]  
            for feature in features:
                feature_range = str(gene_row[feature])
                if '-' in feature_range:
                    start_feature, end_feature = map(int, feature_range.split('-'))
                    if start_feature <= pos <= end_feature:
                        return f"{gene_symbol}:{feature}"
            return 'Outside Gene'
        
        sv_df.at[sv_index, 'breakend1_pos'] = find_feature_position(start_sv, gene_row, strand)
        sv_df.at[sv_index, 'breakend2_pos'] = find_feature_position(end_sv, gene_row, strand)
    
    return sv_df



def annotate_sv_with_additional_info(sv_df, refseq_df):
    sv_df['num_exons_affected'] = 0
    sv_df['num_genes_affected'] = 0

    for index, sv in sv_df.iterrows():
        chrom_sv, start_sv, end_sv = sv['chrom'], sv['start'], sv['end']
        genes_overlapped = sv['gene_symbols']

        if not pd.isna(genes_overlapped):
            sv_df.at[index, 'num_genes_affected'] = len(genes_overlapped.split(','))

        if sv_df.at[index, 'num_genes_affected'] == 1:
            gene_data = refseq_df[(refseq_df['chrom'] == chrom_sv) & (refseq_df['gene_symbol'] == genes_overlapped)].iloc[0]
            exons_affected = set()
            for feature in gene_data.index:
                if 'exon' in feature:
                    feature_range_str = gene_data[feature]
                    if pd.isna(feature_range_str) or '-' not in str(feature_range_str):
                        continue  
                    start_feature, end_feature = map(int, str(feature_range_str).split('-'))
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
    open_func = gzip.open if path.endswith('.gz') else open
    with open_func(path, 'rt') as f:   
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
            except ValueError:  
                return np.nan
    return np.nan

sv_path = "C:/Users/dlhyeung/Downloads/34814-ONT-LIB1.wf_sv.vcf.gz"
#sv_path = "C:/Users/dlhyeung/Downloads/34814-ONT-LIB1.wf_str.vcf.gz"
#sv_path = "C:/Users/dlhyeung/Downloads/test.sv.vcf.gz"
sv_df = read_vcf(sv_path)
sv_df = preprocess_sv_df(sv_df)

refseq_csv_path = 'C:/Users/dlhyeung/Downloads/refseq_denis.tsv'
refseq_df = parse_refseq_for_boundaries_corrected(refseq_csv_path)
refseq_df = reverse_exon_intron_order(refseq_df)
refseq_df.to_csv('C:/Users/dlhyeung/Downloads/refseq.csv')


sv_df = find_genes_for_sv(sv_df)  
sv_df = annotate_sv_positions(sv_df, refseq_df)
sv_df = annotate_sv_with_additional_info(sv_df, refseq_df)
sv_df['SVLEN_ABS'] = sv_df['INFO'].apply(extract_svlen_abs)

#Current function cannot work out number of exons affected across genes
sv_df.loc[sv_df['num_genes_affected'] > 1, 'num_exons_affected'] = np.NaN


# Some genes have more than one transcript with different name from the refseq file (Usually two), and affecting intronic region
# For SVs where num_genes_affected is 2 and breakpoint dont sit in intronic/exonic, and SVLEN_ABS <2000. They are filtered out
# genes have more than one transcript 
final_filtered_sv_df = sv_df[~((sv_df['num_exons_affected'] == 0) & (sv_df['num_genes_affected'] != 2))]
final_filtered_sv_df = final_filtered_sv_df[
    ~(
        (final_filtered_sv_df['num_genes_affected'] == 2) &
        (final_filtered_sv_df['breakend1_pos'] == 'Outside Gene') &
        (final_filtered_sv_df['breakend2_pos'] == 'Outside Gene') &
        (final_filtered_sv_df['SVLEN_ABS'] < 2000)
    )
]

final_filtered_sv_df = final_filtered_sv_df.drop(columns=['SVLEN_ABS'])
final_filtered_sv_df.to_csv('final_filtered.csv', index=False)
print(final_filtered_sv_df.head())


column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
morbid_map = pd.read_csv("C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/morbidmap.txt", sep='\t', names=column_names, header=None)

morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]

valid_morbid_genes = set()
for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
    valid_morbid_genes.update(gene.strip() for gene in genes)


def check_morbid_gene(gene_symbols):
    genes = gene_symbols.split(',')
    morbid_genes = [gene for gene in genes if gene.strip() in valid_morbid_genes]
    return 'Yes' if morbid_genes else 'No'

final_filtered_sv_df['Morbid Gene'] = final_filtered_sv_df['gene_symbols'].apply(check_morbid_gene)
final_filtered_sv_df.to_csv("34814-ONT-LIB1.wf_sv.vcf.csv")
print(final_filtered_sv_df[['gene_symbols', 'Morbid Gene']].head())



