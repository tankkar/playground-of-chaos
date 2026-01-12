import pandas as pd

ID='SRE08820'
genes_file = f"{ID}.genes.tsv"
variants_file = f"{ID}.variants.tsv"

def filter_variants(variant_file):
    variants_df = pd.read_csv(variant_file, sep='\t')
    variants_df['ALL_PATH'] = variants_df['ALL_PATH'].astype(str)
    filtered_variants_df = variants_df[
        ~(
            (variants_df['MAX_PATH_SOURCE'].isin(['REMM', 'MVP'])) & 
            (~variants_df['ALL_PATH'].str.contains(',')) & 
            (variants_df['CLINVAR_PRIMARY_INTERPRETATION'] == 'NOT_PROVIDED')
        )
    ]

    return filtered_variants_df


def filter_top_genes_by_moi(variants_df):
    top_variants = variants_df.loc[variants_df.groupby('GENE_SYMBOL')['EXOMISER_GENE_COMBINED_SCORE'].idxmax()]
    top_variants = top_variants.sort_values(by='EXOMISER_GENE_COMBINED_SCORE', ascending=False).groupby('MOI').head(10).reset_index(drop=True)
    return top_variants

def update_genes(genes_file, filtered_variants_df):
    genes_df = pd.read_csv(genes_file, sep='\t')
    filtered_genes_df = genes_df[genes_df['GENE_SYMBOL'].isin(filtered_variants_df['GENE_SYMBOL'])]
    filtered_genes_df = filtered_genes_df[filtered_genes_df['HUMAN_PHENO_EVIDENCE'].notna() & (filtered_genes_df['HUMAN_PHENO_EVIDENCE'] != '')]
    return filtered_genes_df

genes_output_file = genes_file.replace('.tsv', '_filtered.tsv')
variants_output_file = variants_file.replace('.tsv', '_filtered.tsv')

filtered_variants_df = filter_variants(variants_file)
top_variants_df = filter_top_genes_by_moi(filtered_variants_df)

updated_genes_df = update_genes(genes_file, top_variants_df)
top_variants_df.to_csv(variants_output_file, sep='\t', index=False)
updated_genes_df.to_csv(genes_output_file, sep='\t', index=False)

print(f"Filtered variants saved to {variants_output_file}")
print(f"Updated genes saved to {genes_output_file}")
