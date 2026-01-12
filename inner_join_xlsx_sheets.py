import pandas as pd

df = pd.read_excel("hc-1078samples-merge.h.no-moi-dot_copy.xlsx", sheet_name='hc-1078samples-merge.h.no-moi-d')
old_df2 = pd.read_excel("HC semi-auto result 20240403_11-00 no non-panel genes.xlsx", sheet_name='20240403_11-00')
old_df = pd.read_excel("HC_semi-auto_result 20240419_17-34.xlsx", sheet_name='20240419_17-34 (2)')

df['Previous analysis: R2 comments'] = ''
df['Previous analysis: R2 tentative pathogenicity'] = ''
df['Previous analysis: report this variant?'] = ''

df['sample ID'] = df['sample ID'].astype(str)
old_df['sample'] = old_df['sample'].astype(str)
old_df2['sample'] = old_df2['sample'].astype(str)

old_df['sample'] = old_df['sample'].str.split('_').str[0]
old_df2['sample'] = old_df2['sample'].str.split('_').str[0]

def update_df_with_old_data(df, old_df):
    for index, row in df.iterrows():
        match = old_df[(old_df['sample'] == row['sample ID']) & (old_df['cpra'] == row['cpra'])]
        if not match.empty:
            df.at[index, 'Previous analysis: R2 comments'] = match['R2 comments'].values[0]
            df.at[index, 'Previous analysis: R2 tentative pathogenicity'] = match['R2 tentative pathogenicity'].values[0]
            df.at[index, 'Previous analysis: report this variant?'] = match['report this variant?'].values[0]

update_df_with_old_data(df, old_df)
update_df_with_old_data(df, old_df2)

df.to_excel("test.xlsx", index=False)

