import pandas as pd

def process_to_bed_and_sort(df):
    def process_exons(row):
        starts = [int(x) - 20 for x in row["exonStarts"].split(",") if x.strip()]
        ends = [int(x) + 20 for x in row["exonEnds"].split(",") if x.strip()]
        chrom = row["chrom"]
        return [(chrom, start, end) for start, end in zip(starts, ends)]
    
    bed_rows = [exon for row in df.apply(process_exons, axis=1) for exon in row]
    bed_df = pd.DataFrame(bed_rows, columns=["chrom", "chromStart", "chromEnd"])
    
    bed_df['range'] = bed_df['chromStart'].astype(str) + '-' + bed_df['chromEnd'].astype(str)
    sorted_bed_df = bed_df.sort_values(by=['chrom', 'chromStart', 'chromEnd'])
    
    return sorted_bed_df


df = pd.read_csv("C:/Users/dlhyeung/Downloads/refseq_original.tsv", sep='\t')
sorted_bed_df = process_to_bed_and_sort(df)
sorted_bed_df.to_csv("C:/Users/dlhyeung/Downloads/sorted_bed_df.csv", index=False)

bed_df_final = sorted_bed_df.drop(columns=['range'])
bed_df_final.to_csv("C:/Users/dlhyeung/Downloads/sorted_bed_df.bed", sep='\t', index=False, header=False)

