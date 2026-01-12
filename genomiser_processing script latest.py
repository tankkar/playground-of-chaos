import pandas as pd

df = pd.read_csv('SRE020919_output.variants.tsv', sep='\t')

df['ALL_PATH'] = df['ALL_PATH'].fillna('')

mask = (df['ALL_PATH'].str.startswith('REMM=')) & (~df['ALL_PATH'].str.contains(','))

df = df[~mask]


df['CONTRIBUTING_VARIANT'] = pd.to_numeric(df['CONTRIBUTING_VARIANT'], errors='coerce')

df = df[df['CONTRIBUTING_VARIANT'] == 1]

def add_morbid_gene_column(df):
    column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
    morbid_map = pd.read_csv("C:/Users/dlhyeung/Documents/Rapid LR/resources/morbidmap.txt", sep='\t', names=column_names, header=None)
    print(morbid_map)
    morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
    valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]
    valid_morbid_genes = set()
    for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
        valid_morbid_genes.update(gene.strip() for gene in genes)

    def check_morbid_genes(gene_list):
        genes = [gene.strip() for gene in gene_list.split(',')]
        return 'Yes' if any(gene in valid_morbid_genes for gene in genes) else 'No'

    df['Morbid Gene'] = df['gene_symbols'].apply(check_morbid_genes)
    return df

df = add_morbid_gene_column(df)

excel_file_path = 'C:/Users/dlhyeung/Documents/Vscode/Nanopore_case.xlsx'


# Limit the DataFrame to the first 30 rows
df = df.head(30)

# Optional: Save the filtered DataFrame to a new TSV file
df.to_csv('filtered_data.tsv', sep='\t', index=False)
