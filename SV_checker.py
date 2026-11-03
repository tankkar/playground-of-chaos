import pandas as pd

def read_csv(file_path):
    return pd.read_csv(file_path, low_memory=False)

def is_exonic(df, chrom, start, end=None):
    if end is None:
        end = start
    filtered_df = df[df['chrom'] == chrom]
    exon_columns = [col for col in df.columns if col.startswith('exon')]
    for index, row in filtered_df.iterrows():
        for exon_col in exon_columns:  # Consider only exon columns
            exon_value = row[exon_col]
            if pd.isna(exon_value) or not isinstance(exon_value, str):
                continue
            exon_start, exon_end = map(int, exon_value.split('-'))

            if start <= exon_end and end >= exon_start:
                return True
    return False

def main():
    file_path = r'C:\Users\dlhyeung\Downloads\refseq.csv'
    df = read_csv(file_path)
    check_exonic_region(df)

def check_exonic_region(df):
    chrom = "chrX"
    start =   636667
    end_input =  636726
                        
    if end_input:
        end = int(end_input)
    else:
        end = start
    if is_exonic(df, chrom, start, end):
        print(f"The region {chrom}:{start}-{end} lies within an exonic region.")
    else:
        print(f"The region {chrom}:{start}-{end} does not lie within an exonic region.")

if __name__ == "__main__":
    main()
