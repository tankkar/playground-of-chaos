
import pandas as pd
import requests
import os
import time
from joblib import Parallel, delayed
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


############################ Configuration #######################################
input_directory = "C:/Users/dlhyeung/Documents/Python/mastermind_run"
api_token = 'WXBOVyRGOGaNP98vTOLicdz3xdwc0R0TGkMz54d2OGdCeXye5wHgk7MrXbeTnxJB'
run_HPO = False  # Accept True/False, Perform article count query for each variant associated with each HPO or not

# HPO_terms, accepts tuple or list
HPO_terms = [
    "Phenotypic abnormality (HP:0000118)",
    'Clinical modifier (HP:0012823)',
    'Mode of inheritance (HP:0000005)',
    'Mortality/Aging (HP:0040006)',
    'Abnormal circulating ceruloplasmin concentration (HP:0033144)',
]

# Function definitions
def standardize_columns(df):
    column_mapping = {
        'hgvsc': ['HGVSc', 'HGVSC', 'HGVS'],
        'gene_symbol': ['Gene_symbol', 'Gene_Symbol', 'Gene Symbol', 'Gene symbol', 'gene symbol', 'gene', 'Symbol', 'gene_symbol'],
        'mane_select': ['Mane_select', 'Mane_Select', 'Mane Select', 'Mane select', 'mane select', 'MANE_Select'],
        'Impact': ['impact', 'Impact', 'VarApp_Impact']
    }
    for std_col, variants in column_mapping.items():
        for var in variants:
            if var in df.columns:
                df.rename(columns={var: std_col}, inplace=True)
                break
            
    df.replace(' - ', None, inplace=True)
    return df


def split_variant(variant):
    parts = variant.split(":")
    if len(parts) == 2:
        return parts[1]
    else:
        return variant

def encode_variant(variant):
    if variant is None:
        return ''
    if isinstance(variant, list):
        return [item.replace(':', '%3A').replace('>', '%3E').replace('!', '%21').replace('+', '%2B') if item is not None else '' for item in variant]
    else:
        return variant.replace(':', '%3A').replace('>', '%3E').replace('!', '%21').replace('+', '%2B')

def parse_HPO_terms(HPO_terms):
    hpo_term_codes = []
    if isinstance(HPO_terms, str):  # handles string, haven't tested for multiple strings
        HPO_terms = [HPO_terms]
    for term in HPO_terms:
        match = re.search(r"\(([^)]+)\)", term)
        if match:
            term_code = match.group(1)  # Extracts the text within parentheses
            hpo_term_codes.append(term_code)
    return hpo_term_codes

def get_canonical_variant(gene, variant, encoded_variant, impact):
    gene = str(gene)
    variant = str(variant)
    encoded_variant = str(encoded_variant)
    response = None
    base_url = 'https://mastermind.genomenon.com/api/v2/suggestions?'
    if encoded_variant.startswith('NM'):
        full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    else:
        #full_url = f"{base_url}api_token={api_token}&gene={gene}&variant={encoded_variant}"
        full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    try:
        response = requests.get(full_url, timeout=10)
        print(response)
    except requests.exceptions.Timeout:
        print("Timeout occurred")
        return {'canonical': '.'}
    if response.status_code == 200:
        print("Successfully obtained canonical variant for " + variant)
        return response.json()
    else:
        print("Failed to obtain canonical variant for " + variant)
        return '.'

def get_canonical_variant(gene, variant, encoded_variant, impact):
    gene = str(gene)
    variant = str(variant)
    encoded_variant = str(encoded_variant)
    response = None
    base_url = 'https://mastermind.genomenon.com/api/v2/suggestions?'
    if encoded_variant.startswith('NM'):
        full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    else:
        full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    max_attempts = 8
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(full_url, timeout=10)
            print(response)
        except requests.exceptions.Timeout:
            print("Timeout occurred")
            return {'canonical': '.'}
        
        if response.status_code == 200:
            print("Successfully obtained canonical variant for " + variant)
            return response.json()
        elif response.status_code == 429:
            attempt += 1
            wait_time = 1 
            print(f"Too Many Requests: Retrying in {wait_time} seconds for {variant}...")
            time.sleep(wait_time)
        else:
            print(f"Failed to obtain canonical variant for {variant}. Status code: {response.status_code}")
            return {'canonical': '.'}
    
    print("Maximum retry attempts reached.")
    return {'canonical': '.'}

def extract_canonical(variant_info, mutation_type):
    if not variant_info or variant_info == None or type(variant_info) is str:
        return ".", "."
    
    if not isinstance(variant_info, list) or len(variant_info) == 0:
        return ".", "."
    
    first_variant = variant_info[0]
    first_canonical = first_variant.get("canonical", "")
    first_matched = first_variant.get("matched", "")
    
    if len(variant_info) == 1:
        return first_canonical, first_matched

    for variant in variant_info:
        canonical_name = variant.get('canonical', '')
        matched = variant.get('matched', '')
        if mutation_type == 'frameshift_variant' and canonical_name.endswith('fs'):
            return canonical_name, matched
        if mutation_type == 'missense_variant' and not canonical_name.endswith(('sra', 'srd')):
            return canonical_name, matched
        if mutation_type == 'splice_acceptor_variant' and canonical_name.endswith('sa'):
            return canonical_name, matched
        if mutation_type == 'splice_donor_variant' and canonical_name.endswith('sd'):
            return canonical_name, matched
        if mutation_type == 'splice_region_variant' and canonical_name.endswith(('sra', 'srd', 'sa', 'sd')):
            return canonical_name, matched
        if mutation_type == 'intron_variant' and canonical_name.endswith('int'):
            return canonical_name, matched
        if mutation_type == 'intronic_variant' and canonical_name.endswith(('intd', 'inta')):
            return canonical_name, matched

    return first_canonical, first_matched

def get_mastermind_link(gene, variant, encoded_variant):
    encoded_variant = encode_variant(encoded_variant)
    base_url = 'https://mastermind.genomenon.com/api/v2/counts?'
    full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    
    max_attempts = 8
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(full_url, timeout=10)
            print(response.json())  # debug use
        except requests.exceptions.Timeout:
            print("Timeout occurred")
            return '.'
        
        if response.status_code == 200:
            print("Successfully obtained count number for " + variant)
            return response.json()
        elif response.status_code == 429:
            attempt += 1
            wait_time = 1  
            print(f"Too Many Requests: Retrying in {wait_time} seconds for {variant}...")
            time.sleep(wait_time)
        else:
            print(f"Failed to obtain count number for {variant}. Status code: {response.status_code}")
            return '.'
    
    print("Maximum retry attempts reached.")
    return '.'

def get_mastermind_link_and_update(row):
    if row['canonical_variant'] == '.' or pd.isnull(row['canonical_variant']):
        return (row.name, '.', '.')
    else:
        result = get_mastermind_link(row['gene'], row['variant'], row['canonical_variant'])
        if isinstance(result, dict):
            return (row.name, result.get('article_count', '.'), result.get('url', '.'))
        else:
            return (row.name, '.', '.')


def get_mastermind_link(gene, variant, encoded_variant):
    encoded_variant = encode_variant(encoded_variant)
    base_url = 'https://mastermind.genomenon.com/api/v2/counts?'
    full_url = f"{base_url}api_token={api_token}&variant={encoded_variant}"
    
    max_attempts = 8
    attempt = 0
    while attempt < max_attempts:
        try:
            response = requests.get(full_url, timeout=10)
        except requests.exceptions.Timeout:
            print("Timeout occurred")
            return '.'
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(response_data)  # Debug: Print the JSON response
                print("Successfully obtained count number for " + variant)
                return response_data
            except requests.exceptions.JSONDecodeError:
                print(f"Failed to decode JSON for variant {variant}. Response content:")
                print(response.text)  # Print the raw response content for debugging
                return '.'
        elif response.status_code == 429:
            attempt += 1
            wait_time = 1  
            print(f"Too Many Requests: Retrying in {wait_time} seconds for {variant}...")
            time.sleep(wait_time)
        else:
            print(f"Failed to obtain count number for {variant}. Status code: {response.status_code}")
            print("Response content:")
            print(response.text)  # Print the raw response content for debugging
            return '.'
    
    print("Maximum retry attempts reached.")
    return '.'

def get_mastermind_link_and_update(row):
    if row['canonical_variant'] == '.' or pd.isnull(row['canonical_variant']):
        return (row.name, '.', '.')
    else:
        result = get_mastermind_link(row['gene'], row['variant'], row['canonical_variant'])
        if isinstance(result, dict):
            return (row.name, result.get('article_count', '.'), result.get('url', '.'))
        else:
            return (row.name, '.', '.')



def process_genotypes(df):
    def is_de_novo(proband_genotype, father_genotype, mother_genotype):
        return proband_genotype == '0/1' and father_genotype == '0/0' and mother_genotype == '0/0'
    
    def determine_moi(row):
        parts = row['Samples_genotypes'].split(',')
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

    #df['MOI'] = df.apply(determine_moi, axis=1)
    #df = df[df['MOI'] != 'Drop Row'].reset_index(drop=True)

    ar_genes = df[df['CGD_Inheritance'].str.contains('AR', na=False)]
    compound_het_genes = ar_genes.groupby('gene').filter(lambda g: g['Start'].nunique() > 1)['gene'].unique()

    for gene in compound_het_genes:
        gene_rows = df[df['gene'] == gene]
        if gene_rows['Genotype_qualities'].str.contains('0/1').any():
            df.loc[gene_rows.index, 'MOI'] = 'autosomal recessive (compound het)'

    #gnomad_keys = ['Gnomadv3_af_eas', 'Gnomad_af', 'Gnomad_eas_af', 'Gnomadv3_af']
    #filtered_df = df[~df[gnomad_keys].apply(lambda x: (x >= 0.005).any(), axis=1)]

    return df

def mark_compound_het(df):
    ar_genes = df[df['CGD_Inheritance'].str.contains('AR', na=False)]
    compound_het_genes = ar_genes.groupby('Gene').filter(lambda g: g['Start'].nunique() > 1)['gene_symbol'].unique()

    for gene in compound_het_genes:
        df.loc[
            (df['Gene'] == gene) & 
            df['CGD_Inheritance'].str.contains('AR', na=False), 
            'MOI'
        ] = 'autosomal recessive (compound het)'

    return df

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

def update_row(index):
    try:
        gene_symbol = df.at[index, 'gene_symbol']
        if pd.notnull(gene_symbol):
            uk_panel_name, uk_expert_review = get_gene_info(gene_symbol)
            au_panel_name, au_expert_review = get_gene_info_australia(gene_symbol)
            return index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review
    except Exception as e:
        print(f"Failed to process row {index}: {e}")
        return index, "", "", "", ""

def filter_genotypes(df, column_name='Samples_genotypes'):
    # Function to check if the first person's genotype is invalid
    def first_person_invalid(row):
        samples = row.split(",")
        first_sample = samples[0]
        genotype_pattern = first_sample.split(": ")[1]
        return genotype_pattern == "0/0" or genotype_pattern == "./."
    
    filtered_df = df[~df[column_name].apply(first_person_invalid)]
    
    return filtered_df


for file_name in os.listdir(input_directory):
    if file_name.endswith('.tsv') or file_name.endswith('.csv') or file_name.endswith('.xlsx'):
        start_time = time.time()
        print("Processing " + file_name + "...")
        file_path = os.path.join(input_directory, file_name)
        if file_name.endswith('.tsv'):
            df = pd.read_csv(file_path, sep='\t', comment='#')
        elif file_name.endswith('.csv'):
            df = pd.read_csv(file_path, comment='#')
        elif file_name.endswith('.xlsx', comment='#'):
            df = pd.read_excel(file_path)
        
        df = standardize_columns(df)
        df['gene'] = df['Gene'].str.lower()
        df['variant'] = df['hgvsc'].astype(str)
        df['variant'] = df['variant'].apply(split_variant)
        df = filter_genotypes(df)
        
        #df['mane_select'] = df['MANE_Select']
        #df['mane_select'] = df['mane_select'].astype(str)
        #df['variant'] = df.apply(lambda row: str(row['gene']) + ':' + str(row['variant'])
        #                                       if pd.isna(row['mane_select']) or str(row['mane_select']).lower() in ['nan', '.', '', '-']
        #                                       else str(row['mane_select']) + ':' + str(row['variant']), axis=1)
        #df['variant'] = df['variant'].astype(str)
        #df['encoded_variant'] = df['variant'].astype(str).apply(encode_variant)  


        df['variant'] = df.apply(
            lambda row: str(row['mane_select']) + ':' + str(row['variant']) if pd.notna(row['mane_select']) and str(row['mane_select']).lower() not in ['nan', '.', '', '-']
            else str(row['gene']) + ':' + str(row['variant']) if pd.notna(row['gene']) and str(row['gene']).lower() not in ['nan', '.', '', '-']
            else str(row['RSID']), axis=1
        )

        df['variant'] = df['variant'].astype(str)
        df['encoded_variant'] = df['variant'].astype(str).apply(encode_variant)

        df = process_genotypes(df)
        variant_results = Parallel(n_jobs=5)(delayed(get_canonical_variant)(row['gene'], row['variant'], row['encoded_variant'], row['Impact']) for index, row in df.iterrows())
        results = Parallel(n_jobs=10)(delayed(extract_canonical)(variant_info, row['Impact']) for variant_info, (_, row) in zip(variant_results, df.iterrows()))
        canonical_variants, matched_variants = zip(*results)
        df['canonical_variant'] = canonical_variants
        df['canonical_variant_c'] = matched_variants
        df['article_count'] = '.'
        df['url'] = '.'

        results = Parallel(n_jobs=10)(delayed(get_mastermind_link_and_update)(row) for index, row in df.iterrows()) 
        for index, article_count, url in results:
            df.at[index, 'article_count'] = article_count
            df.at[index, 'url'] = url
            if article_count == '.':
                print(f"Failed to obtain count number for {df.at[index, 'variant']}")   

        if run_HPO:
            try:
                extracted_HPO_terms = parse_HPO_terms(HPO_terms)
                encoded_HPO_terms = encode_variant(parse_HPO_terms(HPO_terms))
                results = Parallel(n_jobs=5)(delayed(get_and_update_HPO_links)(row, encoded_HPO_terms) for index, row in df.iterrows())
                for index, data in results:
                    for hpo_term, hpo_data in data.items():
                        article_count_col_name = f"{hpo_term}_art_count"
                        url_col_name = f"{hpo_term}_url"
                        df.at[index, article_count_col_name] = hpo_data['article_count']
                        df.at[index, url_col_name] = hpo_data['url']
            except Exception as e:
                print(f"An error occurred: {e}")

        df.columns = [col.replace('%3A', ':') for col in df.columns]  
        df['mastermind'] = df['gene'] + ':' + df['variant']
                
        df.drop(columns=['gene', 'variant', 'encoded_variant'], inplace=True)  # can drop canonical_variant if needed
        column_mappings = {'canonical_variant': 'can_var', 'canonical_variant_c': 'match_var', 'article_count': 'art_count', 'url': 'mm_url'}
        df.rename(columns=column_mappings, inplace=True)

        df['ClinVar'] = df['mane_select'] + '(' + df['Gene'] + '):' + df['hgvsc'].str.extract(r':(c\..+)')[0]

        # Drop unnecessary columns
        columns_to_drop = ['Gene Symbol_x', 'Gene Symbol_y', 'Variant', 'Transcript', 'Gene Symbol', 'filename', 'Expert_Review']
        for column in columns_to_drop:
            if column in df.columns:
                df = df.drop(columns=[column])

        # Mark compound hets
        #df = mark_compound_het(df)

        # Get gene info from UK and Australia PanelApps
        df['Expert_Review'] = pd.Series(dtype=object)
        df['UK_Expert_Review'] = pd.Series(dtype=object)
        df['UK_Panel_Name'] = pd.Series(dtype=object)
        df['Australia_Expert_Review'] = pd.Series(dtype=object)
        df['Australia_Panel_Name'] = pd.Series(dtype=object)
        num_threads = 15
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(update_row, index): index for index in df.index}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    result_index, uk_panel_name, uk_expert_review, au_panel_name, au_expert_review = future.result()
                    df.at[result_index, 'UK_Expert_Review'] = uk_expert_review
                    df.at[result_index, 'UK_Panel_Name'] = uk_panel_name
                    df.at[result_index, 'Australia_Expert_Review'] = au_expert_review
                    df.at[result_index, 'Australia_Panel_Name'] = au_panel_name  # Corrected the column name here
                except Exception as e:
                    print(f"Error processing index {index}: {e}")

        # Add morbid map info
        column_names = ['Disease', 'GeneSymbols', 'MIMNumber', 'Location']
        morbid_map = pd.read_csv("C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/morbidmap.txt", sep='\t', names=column_names, header=None)

        morbid_map['GeneSymbols'] = morbid_map['GeneSymbols'].astype(str)
        valid_morbid_map = morbid_map[~morbid_map['Disease'].str.startswith('[')]


        valid_morbid_genes = set()
        for genes in valid_morbid_map['GeneSymbols'].str.split(', '):
            valid_morbid_genes.update(gene.strip() for gene in genes)

        def check_morbid_gene(gene):
            return 'Yes' if gene in valid_morbid_genes else 'No'

        df['Morbid Gene'] = df['Gene'].apply(check_morbid_gene)
        #df['hgvsc_formatted'] = df.apply(
        #    lambda row: f"{row['mane_select']}({row['gene_symbol']}):{row['hgvsc'].split(':')[1]} p({row['HGVSp'].split(':')[1][1:]})", 
        #    axis=1
        #)
        
        pseudo_df = pd.read_csv('C:/Users/dlhyeung/Documents/Python/Curation_Pipeline/ucsc_pseudogene.tsv',sep='\t')
        pseudogene_genes = set(pseudo_df['name2'])

        df['Is_Pseudogene?'] = df['Gene'].isin(pseudogene_genes)
        filtered_df = df[df['Is_Pseudogene?'] == True]
        
 
        # Check guideline status
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

        df['Guideline Status'] = df['Gene'].apply(check_guideline_status)

        # Create a dictionary mapping gene names to disease OMIM URLs
        morbid_map_path = r'C:\Users\dlhyeung\Documents\Python\Curation_Pipeline\morbidmap.txt'
        morbid_map = pd.read_csv(morbid_map_path, sep='\t', header=None, names=['Disease', 'Gene_symbols', 'OMIM', 'Location'])

        #gene_to_disease_omim = {}

        #for _, row in morbid_map.iterrows():
        #    disease_id_match = re.search(r'\d{6}', row['Disease'])
        #    if disease_id_match:
        #        disease_id = disease_id_match.group(0)
        #        disease_omim_url = f"https://omim.org/entry/{disease_id}"
        #        genes = row['Gene_symbols']
        #        if isinstance(genes, str):
        #            genes = [genes]
        #        for gene in genes:
        #            gene_to_disease_omim[gene] = disease_omim_url
        #        def get_disease_omim_url(gene):
        #            return gene_to_disease_omim.get(gene, '')

        #df['OMIM_URL'] = df['gene_symbol'].apply(get_disease_omim_url)

        # Save the final filtered data to a CSV file
        if file_name.endswith('.txt'):
            updated_file_path = file_path.replace('.txt', '_filtered.tsv')
            df.to_csv(updated_file_path, sep='\t', index = False, encoding='utf-8')
        if file_name.endswith('.tsv'):
            updated_file_path = file_path.replace('.tsv', '_annotated.tsv')
            df.to_csv(updated_file_path, sep='\t', index=False, encoding='utf-8')
        elif file_name.endswith('.csv'):
            updated_file_path = file_path.replace('.csv', '_updated.csv')
            df.to_csv(updated_file_path, index=False, encoding='utf-8')
        elif file_name.endswith('.xlsx'):
            updated_file_path = file_path.replace('.xlsx', '_updated.xlsx')
            df.to_excel(updated_file_path, index=False)
        end_time = time.time()
        elapse_time = end_time - start_time
        print("Tasks completed for " + file_name)
        print(f"Processing time: {elapse_time:.2f} seconds")





 


