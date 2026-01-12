import pandas as pd

def read_gene_list(genes_file):
    """
    Reads a line-separated text file of gene names and returns a set of those names.
    """
    with open(genes_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def parse_svtype(info_str, alt_str):
    """
    Given the 'INFO' field (info_str) and 'ALT' field (alt_str),
    parse out whether this variant is a DUP or DEL.
    Returns "DEL", "DUP", or "UNK" if unknown.
    """
    if isinstance(info_str, str):
        info_upper = info_str.upper()
        if "SVTYPE=DEL" in info_upper:
            return "DEL"
        elif "SVTYPE=DUP" in info_upper:
            return "DUP"

    alt_upper = str(alt_str).upper()
    if "<DEL>" in alt_upper:
        return "DEL"
    elif "<DUP" in alt_upper:  # catches <DUP> or <DUP:TANDEM>
        return "DUP"

    return "UNK"  # possibly INS, INV, etc.

def is_within_gene_position(breakend_pos: str) -> bool:
    """
    Returns True if the breakend annotation suggests it is within a gene
    (in an intron, exon, or UTR). Otherwise False.
    Example breakend_pos: 'SNRNP25:intron1', 'KANK1:5' UTR', '.', etc.
    """
    if not isinstance(breakend_pos, str):
        return False
    if breakend_pos == '.':
        return False

    lower = breakend_pos.lower()
    return ('intron' in lower) or ('exon' in lower) or ('utr' in lower)

def is_exon_position(breakend_pos: str) -> bool:
    """
    Returns True if the breakend annotation specifically suggests it is in an exon.
    """
    if not isinstance(breakend_pos, str):
        return False
    if breakend_pos == '.':
        return False
    
    return 'exon' in breakend_pos.lower()

def is_coding_exon(pos: str, flag: str) -> bool:
    """
    Checks if the breakend is truly a coding exon.
    1. 'exon' must appear in pos (e.g. 'ESCO2:exon11').
    2. Neither 3' nor 5' UTR is indicated in the flag.
    """
    if not isinstance(pos, str) or not isinstance(flag, str):
        return False
    
    pos_lower = pos.lower()
    flag_lower = flag.lower()

    # Must have "exon" in pos
    if "exon" not in pos_lower:
        return False

    # If the flag mentions 'utr', consider it not coding
    if "utr" in flag_lower:
        return False

    return True

def calculate_cnv_impact(preloaded_gene_df, cnv_start: int, cnv_end: int, gene_name: str):
    """
    Calculates the impact of a CNV on a gene's coding regions using a preloaded gene DataFrame.
    Returns a dict with keys:
        frame: 'inframe' or 'frameshift'
        affected_exon_bases: count of bases of exons impacted by CNV
        total_protein_coding_bases: total coding bases in exons (excluding UTRs)
    """
    try:
        gene_row = preloaded_gene_df[preloaded_gene_df['gene_symbol'] == gene_name].iloc[0]
    except IndexError:
        return {}

    strand = gene_row['strand']
    exon_count = int(gene_row['exonCount'])
    utr_5_region = gene_row["5'utr_region"]
    utr_3_region = gene_row["3'utr_region"]

    try:
        utr_5_start, utr_5_end = map(int, utr_5_region.split('-'))
        utr_3_start, utr_3_end = map(int, utr_3_region.split('-'))
    except (AttributeError, ValueError):
        utr_5_start, utr_5_end = 0, 0
        utr_3_start, utr_3_end = 0, 0

    exon_columns = [f"exon{i+1}" for i in range(exon_count)]
    exons = gene_row[exon_columns].values.flatten()

    total_protein_coding_bases = 0
    affected_exon_bases = 0

    for exon in exons:
        if pd.isna(exon):
            continue

        exon_start, exon_end = map(int, exon.split('-'))

        # Adjust for UTRs depending on strand
        if strand == '+':
            # 5' UTR
            if utr_5_start < exon_end and utr_5_end >= exon_start:
                if exon_start >= utr_5_start and exon_end <= utr_5_end:
                    # Entire exon in 5'UTR
                    continue
                elif exon_start < utr_5_start < exon_end:
                    exon_start = utr_5_end
                elif exon_start <= utr_5_end < exon_end:
                    exon_start = max(exon_start, utr_5_end)

            # 3' UTR
            if utr_3_start < exon_end and utr_3_end >= exon_start:
                if exon_start >= utr_3_start and exon_end <= utr_3_end:
                    # Entire exon in 3'UTR
                    continue
                elif exon_start < utr_3_start < exon_end:
                    exon_end = utr_3_start
                elif exon_start <= utr_3_end < exon_end:
                    exon_end = min(exon_end, utr_3_start)

        else:  # strand == '-'
            # 5' UTR (minus strand)
            if utr_5_start < exon_end and utr_5_end >= exon_start:
                if exon_start >= utr_5_start and exon_end <= utr_5_end:
                    continue
                elif exon_start < utr_5_start < exon_end:
                    exon_end = utr_5_start
                elif exon_start <= utr_5_end < exon_end:
                    exon_end = min(exon_end, utr_5_start)

            # 3' UTR (minus strand)
            if utr_3_start < exon_end and utr_3_end >= exon_start:
                if exon_start >= utr_3_start and exon_end <= utr_3_end:
                    continue
                elif exon_start < utr_3_start < exon_end:
                    exon_start = utr_3_end
                elif exon_start <= utr_3_end < exon_end:
                    exon_start = max(exon_start, utr_3_end)

        coding_bases = max(0, exon_end - exon_start)
        total_protein_coding_bases += coding_bases

        # Overlap with CNV
        overlap_start = max(cnv_start, exon_start + 1)
        overlap_end = min(cnv_end, exon_end)

        if overlap_start <= overlap_end:
            affected_exon_bases += (overlap_end - overlap_start + 1)

    # frameshift vs inframe
    frame = "inframe" if affected_exon_bases % 3 == 0 else "frameshift"

    return {
        "frame": frame,
        "affected_exon_bases": affected_exon_bases,
        "total_protein_coding_bases": total_protein_coding_bases
    }

def process_dataframe(df, preloaded_gene_df, gene_list):
    """
    Processes the main DataFrame, annotating:
      - 'within_gene' (Yes/No) from breakend annotations
      - 'involve_exon' (Yes/No) if either breakend is in an exon
      - 'involve_coding_exon' (Yes/No) if breakend is truly coding (exon w/o UTR)
      - 'frame', 'percent_removed', 'type'
      - 'remark', with updated logic:
         * If deletion + '3' UTR to body' + percent_removed>0 + affected_exons >=2 => "pathogenic; 3' UTR to body"
    """

    # Identify if the SV is within a gene
    df['within_gene'] = df.apply(
        lambda row: "Yes" if (
            is_within_gene_position(row.get('breakend1_pos', '')) or
            is_within_gene_position(row.get('breakend2_pos', ''))
        ) else "No",
        axis=1
    )

    # Identify if the SV involves an exon (regardless of UTR)
    df['involve_exon'] = df.apply(
        lambda row: "Yes" if (
            is_exon_position(row.get('breakend1_pos', '')) or
            is_exon_position(row.get('breakend2_pos', ''))
        ) else "No",
        axis=1
    )

    # Identify if the SV involves a coding exon (exon with no UTR)
    df['involve_coding_exon'] = df.apply(
        lambda row: "Yes" if (
            is_coding_exon(row.get('breakend1_pos', ''), row.get('breakend1_flag', '')) or
            is_coding_exon(row.get('breakend2_pos', ''), row.get('breakend2_flag', ''))
        ) else "No",
        axis=1
    )

    # Initialize final annotation columns
    df['frame'] = None
    df['percent_removed'] = None
    df['type'] = None
    df['remark'] = None

    for index, row in df.iterrows():
        cnv_start = row['start']
        cnv_end = row['end']

        # Parse SV type (DEL/DUP)
        sv_type_detected = parse_svtype(row.get('INFO', ''), row.get('ALT', ''))
        is_del = (sv_type_detected == "DEL")
        is_dup = (sv_type_detected == "DUP")

        # If no gene symbols, skip gene-level logic
        if pd.isna(row['gene_symbols']):
            continue

        # Split out the genes in this row
        genes_in_this_row = row['gene_symbols'].split(',')

        # We'll parse exons_affected for each gene in the same order
        exons_affected_str = row.get('exons_affected_each_gene', '')
        if exons_affected_str:
            exons_affected_list = [int(x.strip()) for x in exons_affected_str.split(',')]
        else:
            exons_affected_list = []

        # Genes that overlap with our panel
        panel_genes = set(genes_in_this_row).intersection(gene_list)

        # Accumulators for textual output
        frame_results = []
        percent_removed_results = []
        type_results = []
        remark_results = []

        for gene_name in panel_genes:
            # Find the index of this gene in the row's gene_symbols
            try:
                gene_index = genes_in_this_row.index(gene_name)
            except ValueError:
                # if not found for some reason, skip
                continue

            # Attempt to retrieve the exons_affected for this gene
            if 0 <= gene_index < len(exons_affected_list):
                exons_affected_for_this_gene = exons_affected_list[gene_index]
            else:
                exons_affected_for_this_gene = 0

            # Pull the gene definition row
            gene_data = preloaded_gene_df[preloaded_gene_df['gene_symbol'] == gene_name]
            if gene_data.empty:
                continue

            strand = gene_data.iloc[0]['strand']
            try:
                f_utr_start, f_utr_end = map(int, gene_data.iloc[0]["5'utr_region"].split('-'))
                t_utr_start, t_utr_end = map(int, gene_data.iloc[0]["3'utr_region"].split('-'))
            except (ValueError, AttributeError, IndexError):
                continue

            gene_numeric_start = min(f_utr_start, f_utr_end, t_utr_start, t_utr_end)
            gene_numeric_end = max(f_utr_start, f_utr_end, t_utr_start, t_utr_end)

            cnv_left, cnv_right = cnv_start, cnv_end

            # Classify region
            if (cnv_left <= gene_numeric_start) and (cnv_right >= gene_numeric_end):
                sv_region = "Whole gene affected"
            else:
                if strand == '+':
                    if cnv_left <= gene_numeric_start and cnv_right < gene_numeric_end:
                        sv_region = "5' UTR to body"
                    elif cnv_left > gene_numeric_start and cnv_right >= gene_numeric_end:
                        sv_region = "3' UTR to body"
                    elif (gene_numeric_start < cnv_left < gene_numeric_end and
                          gene_numeric_start < cnv_right < gene_numeric_end):
                        sv_region = "Within gene"
                    else:
                        sv_region = "Undefined"
                else:  # strand == '-'
                    if cnv_left <= gene_numeric_start and cnv_right < gene_numeric_end:
                        sv_region = "3' UTR to body"
                    elif cnv_left > gene_numeric_start and cnv_right >= gene_numeric_end:
                        sv_region = "5' UTR to body"
                    elif (gene_numeric_start < cnv_left < gene_numeric_end and
                          gene_numeric_start < cnv_right < gene_numeric_end):
                        sv_region = "Within gene"
                    else:
                        sv_region = "Undefined"

            # Calculate coding impact
            result = calculate_cnv_impact(preloaded_gene_df, cnv_left, cnv_right, gene_name)
            if not result:
                continue

            total_coding_bases = result['total_protein_coding_bases']
            affected_bases = result['affected_exon_bases']
            frame = result['frame']  # "inframe" or "frameshift"

            if total_coding_bases > 0:
                pct_removed = (affected_bases / total_coding_bases) * 100
            else:
                pct_removed = 0.0

            # Build aggregator text
            frame_results.append(f"{gene_name}: {frame}")
            percent_removed_results.append(f"{gene_name}: {pct_removed:.2f}%")
            type_results.append(f"{gene_name}: {sv_region}")

            # -- REMARK LOGIC --
            # a) DUP or DEL + 'Within gene' + frameshift => "pathogenic; frameshift"
            if (is_dup or is_del) and (sv_region == "Within gene") and (frame == "frameshift"):
                remark_results.append("pathogenic; frameshift")

            # b) Deletion + "Whole gene affected" => "pathogenic; whole gene deletion"
            elif is_del and (sv_region == "Whole gene affected"):
                remark_results.append("pathogenic; whole gene deletion")

            # c) Deletion + "3' UTR to body" + pct_removed>0 + exons_affected_for_this_gene >=2
            elif is_del and (sv_region == "3' UTR to body"):
                if (pct_removed > 0) and (exons_affected_for_this_gene >= 2):
                    remark_results.append("pathogenic; 3' UTR to body")

            # d) Deletion + "5' UTR to body" + pct_removed>0 => "pathogenic; 5' UTR to body"
            elif is_del and (sv_region == "5' UTR to body") and (pct_removed > 0):
                remark_results.append("pathogenic; 5' UTR to body")

        # Store aggregated strings back into this row
        df.at[index, 'frame'] = "; ".join(frame_results)
        df.at[index, 'percent_removed'] = "; ".join(percent_removed_results)
        df.at[index, 'type'] = "; ".join(type_results)

        # Remove any duplicate remarks while preserving order
        seen = set()
        unique_remarks = []
        for r in remark_results:
            if r not in seen:
                seen.add(r)
                unique_remarks.append(r)

        df.at[index, 'remark'] = "; ".join(unique_remarks)

    return df













if __name__ == "__main__":
    # Replace with your actual file paths
    gene_definition_file = "parsed_refseq.csv"               # Your preloaded gene info in CSV
    input_dataframe_file = "merged_sv_carrier_screening.tsv"  # The CNV data input (TSV)
    genes_txt_file = "HI30_gene_list.txt"                    # Line-separated gene names
    output_file = "merged_sv_carrier_screening_processed_v3.csv"

    # Read gene definitions
    preloaded_gene_df = pd.read_csv(gene_definition_file)

    # Read the CNV data DataFrame (TSV)
    input_dataframe = pd.read_csv(input_dataframe_file, sep='\t')

    # Read the gene list
    gene_list = read_gene_list(genes_txt_file)

    # Process
    output_dataframe = process_dataframe(input_dataframe, preloaded_gene_df, gene_list)

    # Save
    output_dataframe.to_csv(output_file, index=False)
    print(output_dataframe)
