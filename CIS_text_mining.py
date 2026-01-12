import os
import json
from pdf2image import convert_from_path
import pytesseract
from FastHPOCR.HPOAnnotator import HPOAnnotator

os.chdir(r"C:\Users\dlhyeung\Documents\Python\Curation_Pipeline\PNICU rapid case CIS notes")

TESSERACT_CMD = r"C:\Users\dlhyeung\AppData\Local\miniconda3\envs\CIS_text_mining\Library\bin\tesseract.exe"
POPPLER_PATH = r"C:\Users\dlhyeung\AppData\Local\miniconda3\envs\CIS_text_mining\Library\bin"
    
HPO_INDEX_FILE = os.path.abspath(os.path.join("..", "hpo_index", "hp.index"))

def perform_ocr(pdf_path, poppler_path, tesseract_cmd):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
    full_text = ""
    for i, page in enumerate(pages, start=1):
        full_text += f"\n\n--- Page {i} ---\n\n"
        full_text += pytesseract.image_to_string(page, lang="eng")
    return full_text

def annotate_text(text, index_file):
    annotator = HPOAnnotator(index_file)
    annotations = annotator.annotate(text)
    serializable = []
    for ann in annotations:
        serializable.append(ann.__dict__)
    return serializable


def deduplicate_annotations(annotations):
    seen_uris = set()
    deduplicated = []
    for ann in annotations:
        uri = ann["hpoUri"]
        if uri not in seen_uris:
            seen_uris.add(uri)
            deduplicated.append(ann)
    return deduplicated

for filename in os.listdir():
    if filename.lower().endswith('.pdf'):
        pdf_path = filename
        base_name = os.path.splitext(filename)[0]
        OCR_TEXT_FILE = f"{base_name}_ocr.txt"
        ANNOT_JSON_FILE = f"{base_name}_annotations.json"
        
        ocr_text = perform_ocr(pdf_path, POPPLER_PATH, TESSERACT_CMD)
        with open(OCR_TEXT_FILE, "w", encoding="utf-8") as f:
            f.write(ocr_text)
        print(f"✅ OCR complete — see {OCR_TEXT_FILE}")
        
        annotations = annotate_text(ocr_text, HPO_INDEX_FILE)
        deduplicated_annotations = deduplicate_annotations(annotations)
        with open(ANNOT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(deduplicated_annotations, f, indent=2)
