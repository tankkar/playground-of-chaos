#!/usr/bin/env python3
##########################Part 1 index HPO cache###########################
import os
from FastHPOCR.IndexHPO import IndexHPO
from FastHPOCR.HPOAnnotator import HPOAnnotator
# Optional index configuration (adjust as needed)
indexConfig = {
    'rootConcepts': ['HP:0000118'],
    'allow3LetterAcronyms': True,  # set to True if you want to include them
    'includeTopLevelCategory': True,      # adds extra concept info if available
    'allowDuplicateEntries': False        # change to True to allow duplicates
}

hpoFileLocation = "hp.obo"

outputFolder = "hpo_index2"
if not os.path.exists(outputFolder):
    os.makedirs(outputFolder)

indexHPO = IndexHPO(hpoFileLocation, outputFolder, indexConfig=indexConfig)
indexHPO.index()
print("Indexing complete. Index stored in:", outputFolder)

##########################################################################  
####################Part 2 OCR and annotate HPO terms#####################
import os
import re
import math
import json
from pdf2image import convert_from_path
import pytesseract
from FastHPOCR.HPOAnnotator import HPOAnnotator
import csv
import pandas as pd 
TESSERACT_CMD   = r"C:\Users\dlhyeung\AppData\Local\miniconda3\envs\CIS_text_mining\Library\bin\tesseract.exe"
POPPLER_PATH    = r"C:\Users\dlhyeung\AppData\Local\miniconda3\envs\CIS_text_mining\Library\bin"
#HPO_INDEX_FILE  = os.path.abspath(os.path.join("..", "hpo_index2", "hp.index"))
HPO_INDEX_FILE = r'C:\Users\dlhyeung\Documents\Python\Curation_Pipeline\hpo_index2\hp.index'
INPUT_DIR       = r"C:\Users\dlhyeung\Documents\Python\Curation_Pipeline\PNICU rapid case CIS notes\temp"
NUM_CHUNKS      = 4            # force into 4 pieces
MIN_LINE_LEN    = 6            # drop very short noise lines

def perform_ocr(pdf_path):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    parts = []
    for i, img in enumerate(images, start=1):
        txt = pytesseract.image_to_string(img, lang="eng")
        parts.append(f"--- Page {i} ---\n\n{txt}")
    return "\n\n".join(parts)

def clean_ocr(text):
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if len(ln) >= MIN_LINE_LEN]
    return "\n".join(lines)

def chunk_text_into_n(text, n):
    length = len(text)
    chunk_size = math.ceil(length / n)
    return [ text[i:i+chunk_size] for i in range(0, length, chunk_size) ]

def annotate_and_collect(chunks, annotator):
    all_anns = []
    for chunk in chunks:
        for ann in annotator.annotate(chunk):
            all_anns.append(ann.__dict__)
    return all_anns

def dedupe_annotations(anns):
    seen = set()
    unique = []
    for ann in anns:
        uri = ann.get("hpoUri")
        if uri and uri not in seen:
            seen.add(uri)
            unique.append(ann)
    return unique




def main():
    os.chdir(INPUT_DIR)
    annotator = HPOAnnotator(HPO_INDEX_FILE)
    
    # Initialize merged CSV data
    merged_data = []
    fieldnames = ["Case ID", "HPO Term", "HPO Term Category", "FastHPOCR"]

    for pdf in sorted(os.listdir()):
        if not pdf.lower().endswith(".pdf"):
            continue

        base = os.path.splitext(pdf)[0]
        print(f"\n[*] Processing {pdf}")

        # 1) OCR + clean
        raw_text = perform_ocr(pdf)
        clean_text = clean_ocr(raw_text)

        # 2) Save full cleaned OCR text
        full_fname = f"{base}_ocr_full.txt"
        with open(full_fname, "w", encoding="utf-8") as f:
            f.write(clean_text)

        # 3) Split into chunks and write them
        chunks = chunk_text_into_n(clean_text, NUM_CHUNKS)
        for idx, chunk in enumerate(chunks, start=1):
            fname = f"{base}_ocr_chunk{idx}.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(chunk)

        # 4) Annotate all chunks and combine
        all_anns = annotate_and_collect(chunks, annotator)

        # 5) Deduplicate and output JSON + CSV
        unique = dedupe_annotations(all_anns)

        # Extract sample ID
        sample_id = base.split("_")[0]

        # Save JSON
        json_fname = f"{base}_annotations.json"
        with open(json_fname, "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2)
        print(f"    • Saved {len(unique)} unique annotations: {json_fname}")

        # Process annotations for merged CSV
        for ann in unique:
            # Extract categories
            categories = ann.get("categories", [])
            category_labels = [cat.get("label", "") for cat in categories]
            hpo_category = "; ".join(category_labels) or "Uncategorized"
            
            # Format HPO term
            hpo_term = f"{ann.get('textSpan', '')} ({ann.get('hpoUri', '')})"
            
            # Add to merged data
            merged_data.append({
                "Case ID": sample_id,
                "HPO Term": hpo_term,
                "HPO Term Category": hpo_category,
                "FastHPOCR": "Yes"
            })

    # Write merged CSV
    merged_csv = "all_case_hpo_annotations.csv"
    with open(merged_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_data)
    
    print(f"\n[*] Created merged CSV with {len(merged_data)} annotations: {merged_csv}")

if __name__ == "__main__":
    main()
    
    
##########
def extract_categories(ann: dict) -> str:
    cats = ann.get("categories") or ann.get("category") or []
    if isinstance(cats, dict):            # normalise to list
        cats = [cats]

    labels = []
    for c in cats:
        lbl = c.get("label") if isinstance(c, dict) else str(c)
        if lbl:
            labels.append(lbl.strip())

    return "; ".join(sorted(set(labels))) or "Uncategorised"
# ───────────────────────────────────────────────────────────────

def main():
    import os
    import json
    import pandas as pd
    
    os.chdir(INPUT_DIR)
    annotator = HPOAnnotator(HPO_INDEX_FILE)

    merged_data = []
    fieldnames = [
        "Case ID", 
        "textSpan",           # New column for the exact matched text
        "HPO Term ID", 
        "HPO Term", 
        "HPO Term Category", 
        "FastHPOCR"
    ]

    for pdf in sorted(os.listdir()):
        if not pdf.lower().endswith(".pdf"):
            continue

        base = os.path.splitext(pdf)[0]
        print(f"\n[*] Processing {pdf}")
        
        # 1) OCR + clean
        raw_text = perform_ocr(pdf)
        clean_text = clean_ocr(raw_text)

        # 2) Save full cleaned OCR text
        with open(f"{base}_ocr_full.txt", "w", encoding="utf-8") as f:
            f.write(clean_text)

        # 3) Split into chunks
        chunks = chunk_text_into_n(clean_text, NUM_CHUNKS)
        for idx, chunk in enumerate(chunks, 1):
            with open(f"{base}_ocr_chunk{idx}.txt", "w", encoding="utf-8") as f:
                f.write(chunk)

        # 4) Annotate and deduplicate
        all_anns = annotate_and_collect(chunks, annotator)
        unique = dedupe_annotations(all_anns)
        print(unique)
        
        # 5) Save per-file JSON
        with open(f"{base}_annotations.json", "w", encoding="utf-8") as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)
        print(f"    • Saved {len(unique)} unique annotations")

        sample_id = base.split("_")[0]

        # Collect annotations for final CSV
        for ann in unique:
            hpo_id = ann.get("hpoUri", "")
            hpo_term = ann.get("hpoLabel", ann.get("label", ""))
            text_span = ann.get("textSpan", "")  # Extract the matched text
            categories = "; ".join(
                cat["label"] for cat in ann.get("categories", [])
            )
            
            merged_data.append({
                "Case ID": sample_id,
                "textSpan": text_span,
                "HPO Term ID": hpo_id,
                "HPO Term": f"{hpo_term} ({hpo_id})" if hpo_id else hpo_term,
                "HPO Term Category": categories,
                "FastHPOCR": "Yes"
            })
    
    # Write final CSV
    if merged_data:
        df = pd.DataFrame(merged_data, columns=fieldnames)
        df.to_csv("all_case_hpo_annotations.csv", index=False, encoding='utf-8-sig')
        print(f"\n[*] Created merged CSV with {len(merged_data)} annotations")
        print(f"    • Columns: {', '.join(fieldnames)}")
    else:
        print("\n[*] No annotations found. CSV not created.")

if __name__ == "__main__":
    main()
