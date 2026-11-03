import pandas as pd
import os

def create_full_paths(row, windows_base, linux_base):
    if pd.isna(row['Directory Name in NAS']):
        return None, None  
    windows_path = os.path.join(windows_base, row['Directory Name in NAS'], row['Library ID'])
    if windows_path.endswith('\\'):
        windows_path = windows_path[:-1]
    linux_path = windows_path.replace(windows_base.rstrip('\\'), linux_base).replace('\\', '/')
    return windows_path, linux_path

excel_file_path = 'C:/Users/dlhyeung/Documents/Vscode/Nanopore_case.xlsx'
full_df = pd.read_excel(excel_file_path, sheet_name='Lab', header=None)

sample_id_df = full_df.iloc[2:, [1, 22, 26, 30]]
sample_id_df.columns = ['Sample ID', 'Library ID', 'Flow Cell ID', 'Directory Name in NAS']
sample_id_df.reset_index(drop=True, inplace=True)
sample_id_df['Sample ID'] = sample_id_df['Sample ID'].fillna(method='ffill')
sample_id_df['Library ID'] = sample_id_df['Library ID'].astype(str).str.strip()

windows_base_path = 'Z:\\prom\\'
linux_base_path = '/data/network'

sample_id_df['Z Drive File Path'], sample_id_df['Linux Full Path'] = zip(*sample_id_df.apply(
    lambda row: create_full_paths(row, windows_base_path, linux_base_path), axis=1))

sample_id_df['Z Drive Exists?'] = sample_id_df['Z Drive File Path'].apply(
    lambda path: os.path.exists(path) if path else False)

print(sample_id_df[['Sample ID', 'Z Drive File Path', 'Z Drive Exists?', 'Linux Full Path']].head())

sample_id_df.rename(columns={'Sample ID': 'Sample', 'Linux Full Path': 'Data Transfer Directory'}, inplace=True)
columns_order = ['Sample', 'Flow Cell ID', 'Data Transfer Directory', 'Z Drive File Path', 'Z Drive Exists?']
sample_id_df = sample_id_df[columns_order]

print(sample_id_df.head())

output_excel_path = "C:/Users/dlhyeung/Documents/Vscode/full_paths.xlsx"
sample_id_df.to_excel(output_excel_path, index=False)









