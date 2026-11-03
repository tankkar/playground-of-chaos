import pandas as pd
import re

#USER INPUT


#test_file = pd.read_excel("C:/Users/dlhyeung/Documents/test/2.CH000011.xlsx")
#test_file = pd.read_csv("C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/tsv_dump/CH001388.txt", sep = '\t')
#test_file = pd.read_excel("C:/Users/dlhyeung/Documents/Python/website/Curation_Pipeline/#case_train.xlsx")
#test_file = pd.read_csv("C:/Users/dlhyeung/Documents/Python/website/Curation_Pipeline/case_train.csv")


file_path = "C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/tsv_dump/CH001454.tsv"
file_path = "C:/Users/dlhyeung/Documents/Python/Basic_annotation/PW001243.tsv"
sample_id = file_path.split('/')[-1].split('.')[0]  # Use '\\' instead of '/' if you're on Windows
test_file = pd.read_csv(file_path, sep='\t')

####
#def parse_hpo_terms(text):
    ## Use a regular expression to find all instances of the pattern HP: followed by exactly 7 digits
    #hpo_pattern = re.compile(r'HP:\d{7}')
    #hpo_matches = hpo_pattern.findall(text)
    #hpo_terms = list(dict.fromkeys(hpo_matches))
    #return hpo_terms

#text_input = ("Ataxia HP:0001251Nystagmus HP:0000639Unsteady gait HP:0002317Action tremor HP:0002345Broad-based gait HP:0002136Cerebellar atrophy HP:0001272Involuntary movements HP:0004305Generalized hyperreflexia HP:0007034")

#hpo_terms = parse_hpo_terms(text_input)
#print("hpo_terms =", hpo_terms)


#exonic_variants = [
#    'synonymous_variant', 'missense_variant', 'stop_gained', 'stop_lost', 'start_lost','start_retained_variant',
#    'frameshift_variant', 'inframe_insertion', 'inframe_deletion',
#    'splice_acceptor_variant', 'splice_donor_variant', 'splice_region_variant', 'protein_altering_variant' 
#]
#test_file = test_file[test_file['Gene_symbol'].str.upper() == 'CUX2']
#test_file = test_file[test_file['Impact'].isin(exonic_variants)]

#panel_file = pd.read_excel("C:/Users/dlhyeung/Documents/Python/combined_panel.xlsx")
#panel_file = panel_file.dropna(subset=['Gene Symbol'])

#summarized_data = panel_file.groupby('Gene Symbol').agg(filename=('filename', lambda x: ";".join(x.unique()))).reset_index()
#test_file = test_file.merge(summarized_data, left_on='Gene_symbol', right_on='Gene Symbol', how='left')

test_file[['Transcript', 'Variant']] = test_file['HGVSc'].str.split(':', expand=True)  #only old tsv
test_file.rename(columns={'Gene_symbol': 'gene', 'MANE select': 'NM'}, inplace=True)

def get_matching_rows(gene_name, combined_panel_data):
    return combined_panel_data[combined_panel_data['Gene Symbol'] == gene_name]

def get_hits(data, combined_panel_data):
    results = {}
    for gene_name in data['gene'].unique():
        matched_rows = get_matching_rows(gene_name, combined_panel_data)
        matched_rows = matched_rows[matched_rows['Sources(; separated)'].str.contains('Green', case=False, na=False)]
        if not matched_rows.empty:
            results[gene_name] = matched_rows
    combined_results = pd.concat(results.values(), ignore_index=True)
    return combined_results

#hits = get_hits(data2, panel_file)
#hits['Symp'] = hits['HPO'].str.extract(r'^([^;]+)')
#hits['HPO'] = hits['HPO'].str.extract(r'(HP:\d+)')


#gene_hpo_hits = hits.groupby('Gene Symbol').apply(lambda x: pd.Series({
#    'HPO_hit_count': (x['HPO'].isin(hpo_terms)).sum(),
#    'Matching_HPO_terms': ", ".join(x['HPO'][x['HPO'].isin(hpo_terms)])})).reset_index()

#test_file_with_hits = test_file.merge(gene_hpo_hits, left_on='gene', right_on='Gene Symbol', how='left')
def process_genotypes(df):
    # Define the logic for checking de novo mutations
    def is_de_novo(proband_genotype, father_genotype, mother_genotype):
        return proband_genotype == '0/1' and father_genotype == '0/0' and mother_genotype == '0/0'
    
    # Determine the MOI based on the genotype information
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

    # Apply the determine_moi function to each row to set the MOI
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

# Assuming df is your DataFrame
filtered_data = process_genotypes(test_file)
filtered_data['mastermind'] = filtered_data['gene'] + ':' + filtered_data['Variant']
filtered_data['ClinVar'] = filtered_data['Mane_select'] + '(' + filtered_data['gene'] + '):' + filtered_data['HGVSc'].str.extract(r':(c\..+)')[0]
columns_to_drop = ['Gene Symbol_x', 'Gene Symbol_y', 'Variant', 'Transcript', 'Gene Symbol', 'filename','Expert_Review']

for column in columns_to_drop:
    if column in filtered_data.columns:
        filtered_data = filtered_data.drop(columns=[column])

def mark_compound_het(df):
    # Identify genes with AR inheritance and multiple distinct Start positions
    ar_genes = df[df['Cgd_inheritance'].str.contains('AR', na=False)]
    compound_het_genes = ar_genes.groupby('gene').filter(lambda g: g['Start'].nunique() > 1)['gene'].unique()

    for gene in compound_het_genes:
        df.loc[
            (df['gene'] == gene) & 
            df['Cgd_inheritance'].str.contains('AR', na=False), 
            'MOI'
        ] = 'autosomal recessive (compound het)'

    return df

filtered_data = mark_compound_het(filtered_data)


import requests 
from concurrent.futures import ThreadPoolExecutor, as_completed
import time 
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
            
            # Check for next page
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
            
            # Check for next page
            next_page_url = data.get('next', None)

        return ', '.join(panel_names), ', '.join(expert_reviews)
    except Exception as e:
        print(f"Error fetching gene info for {gene_symbol} from Australia PanelApp: {e}")
        return '', ''


def update_row(index):
    try:
        gene_symbol = filtered_data.at[index, 'gene']
        if pd.notnull(gene_symbol):
            uk_panel_name, uk_expert_review = get_gene_info(gene_symbol)
            au_panel_name, au_expert_review = get_gene_info_australia(gene_symbol)
            return index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review
    except Exception as e:
        print(f"Failed to process row {index}: {e}")
        return index, "", "", "", ""


filtered_data['Expert_Review'] = pd.Series(dtype=object)
filtered_data['UK_Expert_Review'] = pd.Series(dtype=object)
filtered_data['UK_Panel_Name'] = pd.Series(dtype=object)
filtered_data['Australia_Expert_Review'] = pd.Series(dtype=object)
filtered_data['Australia_Panel_Name'] = pd.Series(dtype=object)
num_threads = 15
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    futures = {executor.submit(update_row, index): index for index in filtered_data.index}
    for future in as_completed(futures):
        index = futures[future]
        try:
            result_index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review = future.result()
            filtered_data.at[result_index, 'UK_Expert_Review'] = uk_expert_review
            filtered_data.at[result_index, 'UK_Panel_Name'] = uk_panel_name
            filtered_data.at[result_index, 'Australia_Expert_Review'] = au_expert_review
            filtered_data.at[result_index, 'Australia_Panel_Name'] = au_panel_name  # Corrected the column name here
        except Exception as e:
            print(f"Error processing index {index}: {e}")
            
import pandas as pd

column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
morbid_map = pd.read_csv("C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/morbidmap.txt", sep='\t', names=column_names, header=None)

morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]

valid_morbid_genes = set()
for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
    valid_morbid_genes.update(gene.strip() for gene in genes)

def check_morbid_gene(gene):
    return 'Yes' if gene in valid_morbid_genes else 'No'

filtered_data['Morbid Gene'] = filtered_data['gene'].apply(check_morbid_gene)
filtered_data['hgvsc_formatted'] = df.apply(
    lambda row: f"{row['mane_select']}({row['gene_symbol']}):{row['hgvsc'].split(':')[1]} p({row['HGVSp'].split(':')[1][1:]})", 
    axis=1
)


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

morbid_map_path = r'C:\Users\dlhyeung\Documents\Python\Curation_Pipeline\morbidmap.txt'

# Load morbid map data from the file
morbid_map = pd.read_csv(morbid_map_path, sep='\t', header=None, names=['Disease', 'Gene_symbols', 'OMIM', 'Location'])

# Create a dictionary mapping gene names to disease OMIM URLs
gene_to_disease_omim = {}
for _, row in morbid_map.iterrows():
    # Extract the OMIM ID from the disease column
    disease_id_match = re.search(r'\d{6}', row['Disease'])
    if disease_id_match:
        disease_id = disease_id_match.group(0)
        disease_omim_url = f"https://omim.org/entry/{disease_id}"
        genes = row['Gene_symbols'].split(', ')
        for gene in genes:
            gene_to_disease_omim[gene] = disease_omim_url

# Add a new column with OMIM URLs to the filtered_data DataFrame
def get_disease_omim_url(gene):
    return gene_to_disease_omim.get(gene, '')

filtered_data['OMIM_URL'] = filtered_data['gene'].apply(get_disease_omim_url)


filtered_data.to_csv(f'case_{sample_id}.csv', index=False)


# Define a pattern to find and remove the specific number pattern from 'name' except when it's part of the versioning
#pattern = re.compile(r'\s\d+\.\d+(?=\s|$)')
#['proforma'] = df.apply(lambda row: re.sub(pattern, '', row['name'].replace('(au)', '').strip()) + f", (V{row['name'].split()[-1]}), {row['evidence'].strip(',')}", axis=1)    
#df.to_excel(sample_id + '_annotated_vcf.xlsx', index = False)

# Assuming 'df' is your DataFrame loaded from 'AU_PanelApp.xlsx'
# Replace 'your_file.xlsx' with the path to your Excel file
#df = read_excel('C:/Users/dlhyeung/Desktop/template/AU_PanelApp.xlsx')
#processed_data = process_data(df)

# Output the DataFrame with the new 'proforma' column
#print(df[['name', 'evidence', 'proforma']])
#df.to_excel("AU_PanelApp.xlsx", index=False)e'] = au_panel_name
#        except Exception as e:
#            print(f"Row update failed for index {index}: {e}")



# Save the updated DataFrame to a CSV file

#################HPO API
#import requests
#import pandas as pd

# List of HPO IDs for which details need to be fetched
#input_hpo_ids = """
#HP:0000729
#HP:0001999
#HP:0000047
###P:0011342
#HP:0000750
#HP:0000041
#HP:0000400
#HP:0001763
#HP:0100710
#HP:0010296
#HP:0000268
#HP:0002190
#HP:0000807
#HP:0001998
#HP:0001518
#HP:0007018
#"""
#hpo_ids = input_hpo_ids.strip().split('\n')
#
#hpo_details = {}
#
#def get_hpo_term_details(hpo_id):
    #response = requests.get(f"http://hpo.jax.org/api/hpo/term/{hpo_id}")
    #if response.status_code == 200:
        #return response.json()
    #else:
        #return None
#
## Loop through each HPO ID and get its details
#for hpo_id in hpo_ids:
    #details = get_hpo_term_details(hpo_id)
    #if details:
        #hpo_details[hpo_id] = details['details']['name']

# Create a DataFrame from the dictionary
#df_hpo = pd.DataFrame(list(hpo_details.items()), columns=['HPO Term', 'Name'])

# Add a combined column with the HPO term and name
#df_hpo['Combined'] = df_hpo['Name'] + " (" + df_hpo['HPO Term'] + ")"

# Save the DataFrame to an Excel file
#output_file = f'{sample_id}_HPO_Terms.xlsx'
#df_hpo.to_excel(output_file, index=False)
#df_hpo.head()  # Display the first few rows of the DataFrame

#####
