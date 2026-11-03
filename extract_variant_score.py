import pandas as pd
import os

exomiser_dir = r'C:\Users\dlhyeung\Documents\Python\Curation_Pipeline'
genomiser_dir = 'path/to/genomiser/output/files'  # Replace with your Genomiser directory

master_sheet = pd.read_csv('genomiser_cohort.csv', dtype=str)

extracted_data = []

for index, row in master_sheet.iterrows():
    sre_id = row['SRE ID']
    hgvs = row['Variant identified (HGVS)']
    variant_type = row['Variant type']
    moi = row['MOI']
    analytic_approach = row['Analytic approach']
    family_number = row['Family#']
    pcid = row['PCID']
    type_of_analysis = row['Type of analysis']

    try:
        gene_symbol = hgvs.split('(')[1].split(')')[0]
    except IndexError:
        gene_symbol = ''
        print(f"Could not extract gene symbol for SRE ID {sre_id}")

    exomiser_output_file = os.path.join(exomiser_dir, f"{sre_id}_output.variants.tsv")
    genomiser_output_file = os.path.join(genomiser_dir, f"{sre_id}_output.variants.tsv")

    exomiser_gene_combined_score = None
    exomiser_gene_pheno_score = None
    exomiser_gene_variant_score = None
    exomiser_variant_score = None

    genomiser_gene_combined_score = None
    genomiser_gene_pheno_score = None
    genomiser_gene_variant_score = None
    genomiser_variant_score = None

    if os.path.isfile(exomiser_output_file):
        variants = pd.read_csv(exomiser_output_file, sep='\t', dtype=str)

        try:
            cDNA_change = hgvs.split(':')[1].split(' ')[0]
        except IndexError:
            cDNA_change = ''
            print(f"Could not extract cDNA change for SRE ID {sre_id}")

        match = variants[
            (variants['GENE_SYMBOL'] == gene_symbol) &
            (variants['HGVS'].str.contains(cDNA_change, na=False)) &
            (variants['MOI'] == moi)
        ]

        if not match.empty:
            variant_row = match.iloc[0]
            exomiser_gene_combined_score = variant_row['EXOMISER_GENE_COMBINED_SCORE']
            exomiser_gene_pheno_score = variant_row['EXOMISER_GENE_PHENO_SCORE']
            exomiser_gene_variant_score = variant_row['EXOMISER_GENE_VARIANT_SCORE']
            exomiser_variant_score = variant_row['EXOMISER_VARIANT_SCORE']
        else:
            print(f"No matching variant found for SRE ID {sre_id} in Exomiser output file.")
    else:
        print(f"Exomiser output file does not exist for SRE ID {sre_id}")

    if os.path.isfile(genomiser_output_file):
        variants = pd.read_csv(genomiser_output_file, sep='\t', dtype=str)

        try:
            cDNA_change = hgvs.split(':')[1].split(' ')[0]
        except IndexError:
            cDNA_change = ''
            print(f"Could not extract cDNA change for SRE ID {sre_id}")

        match = variants[
            (variants['GENE_SYMBOL'] == gene_symbol) &
            (variants['HGVS'].str.contains(cDNA_change, na=False)) &
            (variants['MOI'] == moi)
        ]

        if not match.empty:
            variant_row = match.iloc[0]
            genomiser_gene_combined_score = variant_row['EXOMISER_GENE_COMBINED_SCORE']
            genomiser_gene_pheno_score = variant_row['EXOMISER_GENE_PHENO_SCORE']
            genomiser_gene_variant_score = variant_row['EXOMISER_GENE_VARIANT_SCORE']
            genomiser_variant_score = variant_row['EXOMISER_VARIANT_SCORE']
        else:
            print(f"No matching variant found for SRE ID {sre_id} in Genomiser output file.")
    else:
        print(f"Genomiser output file does not exist for SRE ID {sre_id}")

    extracted_data.append({
        'Family#': family_number,
        'PCID': pcid,
        'SRE ID': sre_id,
        'Type of analysis': type_of_analysis,
        'Variant identified (HGVS)': hgvs,
        'Variant type': variant_type,
        'MOI': moi,
        'Analytic approach': analytic_approach,
        'EXOMISER_GENE_COMBINED_SCORE': exomiser_gene_combined_score,
        'EXOMISER_GENE_PHENO_SCORE': exomiser_gene_pheno_score,
        'EXOMISER_GENE_VARIANT_SCORE': exomiser_gene_variant_score,
        'EXOMISER_VARIANT_SCORE': exomiser_variant_score,
        'GENOMISER_GENE_COMBINED_SCORE': genomiser_gene_combined_score,
        'GENOMISER_GENE_PHENO_SCORE': genomiser_gene_pheno_score,
        'GENOMISER_GENE_VARIANT_SCORE': genomiser_gene_variant_score,
        'GENOMISER_VARIANT_SCORE': genomiser_variant_score,
    })

new_sheet = pd.DataFrame(extracted_data)

new_sheet.to_csv('extracted_variant_scores.csv', index=False)

print("Extraction complete. The new sheet has been saved as 'extracted_variant_scores.csv'.")
