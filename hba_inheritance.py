import pandas as pd

val_df = pd.read_excel('lr_validation_result_20250612.xlsx', sheet_name='all validation cases')
info_df = pd.read_csv('all.sample_info_up_to_20250523.csv')

info_map = info_df.set_index('sre_patient_id')[['father_sre_id', 'mother_sre_id']]
val_df = val_df.merge(info_map, left_on='SRE ID', right_index=True, how='left')

def identify_family(row):
    fam = []
    if pd.notna(row['father_sre_id']) and row['father_sre_id'] in val_df['SRE ID'].values:
        fam.append(row['father_sre_id'])
    if pd.notna(row['mother_sre_id']) and row['mother_sre_id'] in val_df['SRE ID'].values:
        fam.append(row['mother_sre_id'])
    return ';'.join(fam) if fam else 'No'

val_df['Family Included?'] = val_df.apply(identify_family, axis=1)

print(val_df[['Sample ID', 'SRE ID', 'Family Included?']])
