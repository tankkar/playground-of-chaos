import pandas as pd

# Load the hc_20240822.txt file with tab separation
hc_df = pd.read_csv('hc_20240822.txt', sep='\t')
hc_df.columns = [col.strip() for col in hc_df.columns]

# Load the Mapper_for_HC.csv file
mapper_df = pd.read_csv('Mapper_for_HC.csv')

# Select relevant columns from mapper_df for mapping
mapper_df = mapper_df[['SRE ID according to 20240727', 'PCID', 'Sample ID according to organizer']]
mapper_df.columns = [col.strip() for col in mapper_df.columns]

# Merge hc_df with mapper_df on 'sample_id' and 'SRE ID according to 20240727'
hc_df = hc_df.merge(mapper_df, left_on='sample_id', right_on='SRE ID according to 20240727', how='left')
SRE_mapper = pd.read_csv('SRE_mapper.csv')
batch1 = batch1.merge(SRE_mapper, left_on='PCID', right_on='PCID', how='left')

# Load the Sequencing run & curation organizer.xlsx file, sheet 'HKGP'
organizer_df = pd.read_excel('Sequencing run & curation organizer.xlsx', sheet_name='HKGP', engine='openpyxl')

# Merge hc_df with organizer_df on 'Sample ID according to organizer'
hc_df = hc_df.merge(organizer_df[['Sample ID', 'Relationship', 'Sex']], left_on='Sample ID according to organizer', right_on='Sample ID', how='left')

# Drop any duplicate rows
hc_df = hc_df.drop_duplicates()

# Save the updated dataframe to a new CSV file
hc_df.to_csv('hc_20240822_updated.csv', index=False)

print("The hc_20240822.txt file has been successfully updated and saved as hc_20240822_updated.csv.")
