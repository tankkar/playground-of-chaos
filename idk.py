import os
import pandas as pd
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt

# Path to the directory containing the files
directory_path = "C:/Users/dlhyeung/Documents/Python/Basic_annotation"
morbid_map_path = "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/morbidmap.txt"
output_directory = "C:/Users/dlhyeung/Documents/Python/Basic_annotation"

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Load morbid map data from the file
column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
morbid_map = pd.read_csv(morbid_map_path, sep='\t', names=column_names, header=None)

morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]

valid_morbid_genes = set()
for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
    valid_morbid_genes.update(gene.strip() for gene in genes)

def check_morbid_gene(gene):
    return 'Yes' if gene in valid_morbid_genes else 'No'

# Genes with specific guidelines released
genes_with_specific_guidelines = [
    "ABCA4", "ACADVL", "AKT3", "MTOR", "PIK3CA", "PIK3R2", "CDH1", "GATM", "GAMT", "SLC6A8",
    "F8", "F9", "MYH7", "DICER1", "BRCA1", "BRCA2", "SCN1A", "SCN2A", "SCN3A", "SCN8A",
    "SCN1B", "LDLR", "FBN1", "MYOC", "CYP1B1", "SERPING1", "ATM", "PALB2", "ACVRL1", "ENG",
    "APC", "GAA", "RYR1", "ETHE1", "PDHA1", "POLG", "SLC19A3", "HNF1A", "HNF4A", "GCK",
    "ADA", "DCLRE1C", "IL7R", "JAK3", "RAG1", "RAG2", "IL2RG", "SERPINC1", "TP53", "VHL",
    "RPE65", "TCF4", "SLC9A6", "CDKL5", "FOXG1", "MECP2", "UBE3A", "RUNX1", "BRAF", "HRAS",
    "KRAS", "MAP2K1", "MAP2K2", "NRAS", "PTPN11", "RAF1", "RIT1", "SHOC2", "SOS1", "SOS2",
    "ITGA2B", "ITGB3", "PAH", "NAGS", "CPS1", "OTC", "MYBPC3", "TNNI3", "TNNT2", "TPM1", "ACTC1",
    "MYL2", "MYL3"
]

genes_with_guidelines_in_prep = [
    "SOD1", "CTLA4", "PIK3CD", "PIK3R1", "DDC", "RAD51C", "MLH1", "MSH2", "MSH6", "PMS2", "MUTYH", "PKD1",
    "PKD2", "GUCY2D", "GFAP", "CAPN3", "ANO5", "INS", "DNAH5", "DDX41", "NF1", "PAX6",
    "OPA1", "LRRK2", "ABCD1", "GP1BA", "GP1BB", "GP9", "KCNQ1", "MRAS", "LZTR1", "RRAS2",
    "PPP1CB", "CHM"
]

def check_guideline_status(gene_symbol):
    if gene_symbol in genes_with_specific_guidelines:
        return "Yes"
    elif gene_symbol in genes_with_guidelines_in_prep:
        return "Prep"
    else:
        return "No"

# Function to get OMIM URL
def get_disease_omim_url(gene):
    return gene_to_disease_omim.get(gene, '')

# Function to process genotypes
def process_genotypes(df):
    def is_de_novo(proband_genotype, father_genotype, mother_genotype):
        return proband_genotype == '0/1' and father_genotype == '0/0' and mother_genotype == '0/0'
    
    def determine_moi(row):
        parts = row['Genotypes'].split(',')
        if len(parts) < 3:
            return 'Unknown'
        proband, father, mother = parts
        proband_genotype = proband.split(':')[1]
        father_genotype = father.split(':')[1]
        mother_genotype = mother.split(':')[1]
        
        if proband_genotype == '0/0':
            return 'Drop Row'
        elif is_de_novo(proband_genotype, father_genotype, mother_genotype):
            return 'de novo'
        elif row['Chrom'] == 'chrX' and proband_genotype == '0/1':
            return 'X-linked'
        elif proband_genotype == '1/1':
            return 'autosomal recessive'
        elif proband_genotype == '0/1':
            return 'autosomal dominant'
        else:
            return 'Unknown'

    if 'Genotypes' not in df.columns:
        print("Error: 'Genotypes' column is missing in the input file.")
        print("Available columns:", df.columns)
        return pd.DataFrame()  # Return an empty DataFrame to avoid further processing

    df['MOI'] = df.apply(determine_moi, axis=1)
    df = df[df['MOI'] != 'Drop Row'].reset_index(drop=True)
    ar_genes = df[df['Cgd_inheritance'].str.contains('AR', na=False)]
    compound_het_genes = ar_genes.groupby('gene').filter(lambda g: g['Start'].nunique() > 1)['gene'].unique()

    for gene in compound_het_genes:
        gene_rows = df[df['gene'] == gene]
        if gene_rows['Genotypes'].str.contains('0/1').any():
            df.loc[gene_rows.index, 'MOI'] = 'autosomal recessive (compound het)'

    gnomad_keys = ['Gnomadv3_af_eas', 'Gnomad_af', 'Gnomad_eas_af', 'Gnomadv3_af']
    filtered_df = df[~df[gnomad_keys].apply(lambda x: (x >= 0.005).any(), axis=1)]

    return filtered_df

# Function to update gene information
def get_gene_info(gene_symbol):
    try:
        panel_names = []
        expert_reviews = []
        next_page_url = f'https://panelapp.genomicsengland.co.uk/api/v1/genes/{gene_symbol}/'
        
        while next_page_url:
            response = requests.get(next_page_url)
            data = response.json()
            
            for result in data.get('results', []):
                panel_name = result.get('panel', {}).get('name', '')
                if panel_name:
                    panel_names.append(panel_name)

                expert_review_list = [item for item in result.get('evidence', []) if item.startswith('Expert Review')]
                expert_review = ', '.join(expert_review_list)
                if expert_review:
                    expert_reviews.append(expert_review)
            
            next_page_url = data.get('next', None)

        return ', '.join(panel_names), ', '.join(expert_reviews)
    except Exception as e:
        print(f"Error fetching gene info for {gene_symbol}: {e}")
        return '', ''

def get_gene_info_australia(gene_symbol):
    try:
        panel_names = []
        expert_reviews = []
        next_page_url = f'https://panelapp.agha.umccr.org/api/v1/genes/{gene_symbol}/'
        
        while next_page_url:
            response = requests.get(next_page_url)
            data = response.json()
            
            for result in data.get('results', []):
                panel_name = result.get('panel', {}).get('name', '')
                if panel_name:
                    panel_names.append(panel_name)

                expert_review_list = [item for item in result.get('evidence', []) if item.startswith('Expert Review')]
                expert_review = ', '.join(expert_review_list)
                if expert_review:
                    expert_reviews.append(expert_review)
            
            next_page_url = data.get('next', None)

        return ', '.join(panel_names), ', '.join(expert_reviews)
    except Exception as e:
        print(f"Error fetching gene info for {gene_symbol} from Australia PanelApp: {e}")
        return '', ''

def update_row(index, filtered_data):
    try:
        gene_symbol = filtered_data.at[index, 'gene']
        if pd.notnull(gene_symbol):
            uk_panel_name, uk_expert_review = get_gene_info(gene_symbol)
            au_panel_name, au_expert_review = get_gene_info_australia(gene_symbol)
            return index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review
    except Exception as e:
        print(f"Failed to process row {index}: {e}")
        return index, "", "", "", ""

# Function to process each file
def process_file(file_path):
    print(f"Processing file: {file_path}")
    sample_id = os.path.basename(file_path).split('.')[0]
    test_file = pd.read_csv(file_path, sep='\t')
    print(test_file.head(), test_file.columns)
    
    # Ensure required columns are present and rename them
    required_columns = {
        'Gene_symbol': 'gene',
        'MANE select': 'NM',
        'Genotype_qualities': 'Genotypes'
    }
    columns_to_rename = {key: value for key, value in required_columns.items() if key in test_file.columns}
    test_file.rename(columns=columns_to_rename, inplace=True)
    if 'Genotypes' not in test_file.columns:
        print("Error: 'Genotypes' column is missing after renaming. Please check the input file.")
        return
    filtered_data = process_genotypes(test_file)
    if filtered_data.empty:
        print("No data to process after genotype filtering. Skipping file.")
        return
    filtered_data['OMIM_URL'] = filtered_data['gene'].apply(get_disease_omim_url)

    filtered_data['Morbid Gene'] = filtered_data['gene'].apply(check_morbid_gene)
    filtered_data['Guideline Status'] = filtered_data['gene'].apply(check_guideline_status)

    filtered_data['Expert_Review'] = pd.Series(dtype=object)
    filtered_data['UK_Expert_Review'] = pd.Series(dtype=object)
    filtered_data['UK_Panel_Name'] = pd.Series(dtype=object)
    filtered_data['Australia_Expert_Review'] = pd.Series(dtype=object)
    filtered_data['Australia_Panel_Name'] = pd.Series(dtype=object)

    num_threads = 15
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(update_row, index, filtered_data): index for index in filtered_data.index}
        for future in as_completed(futures):
            index = futures[future]
            try:
                result_index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review = future.result()
                filtered_data.at[result_index, 'UK_Expert_Review'] = uk_expert_review
                filtered_data.at[result_index, 'UK_Panel_Name'] = uk_panel_name
                filtered_data.at[result_index, 'Australia_Expert_Review'] = au_expert_review
                filtered_data.at[result_index, 'Australia_Panel_Name'] = au_panel_name
            except Exception as e:
                print(f"Error processing index {index}: {e}")

    output_file = os.path.join(output_directory, f'case_{sample_id}.csv')
    filtered_data.to_csv(output_file, index=False)
    print(f"Completed processing file: {file_path} - Output saved to: {output_file}")

# Loop through the directory and process each file
for filename in os.listdir(directory_path):
    if filename.endswith('.tsv'):
        file_path = os.path.join(directory_path, filename)
        process_file(file_path)