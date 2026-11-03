import os
import json
import pandas as pd
import tempfile
from FastHPOCR.HPOAnnotator import HPOAnnotator

# Initialize HPO annotator
index_file_path = "hpo_index2/hp.index"
hpoAnnotator = HPOAnnotator(index_file_path)

# Load Excel file
excel_file_path = 'clinphen_check_output.xlsx'
try:
    df = pd.read_excel(excel_file_path)
    print(f"Successfully loaded data from {excel_file_path}")
except FileNotFoundError:
    print(f"ERROR: File not found at {excel_file_path}")
    exit(1)

# Verify correct column name exists
if 'Clinical Summary' not in df.columns:
    print("ERROR: 'Clinical Summary' column not found in Excel file")
    print("Available columns:", df.columns.tolist())
    exit(1)

# Add new column for results
df['fastHPOCR output'] = None

# Process each row
print("Processing clinical summaries...")
for idx, row in df.iterrows():
    clinical_text = row['Clinical Summary']
    
    # Skip empty cells
    if pd.isna(clinical_text) or not str(clinical_text).strip():
        print(f"Skipping empty entry at row {idx}")
        continue
    
    try:
        # Get annotations
        annotations = hpoAnnotator.annotate(str(clinical_text))
        
        # Use secure temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmpfile:
            temp_path = tmpfile.name
            # Serialize using library's built-in method
            hpoAnnotator.serialize(annotations, temp_path, includeCategoriesIfPresent=True)
        
        # Read serialized content
        with open(temp_path, 'r') as f:
            json_content = f.read()
        
        # Clean up temp file immediately
        os.unlink(temp_path)
        
        # Store in DataFrame
        df.at[idx, 'fastHPOCR output'] = json_content
        print(f"Processed row {idx}: Found {len(annotations)} annotations")
    
    except Exception as e:
        error_msg = f"ERROR processing row {idx}: {str(e)}"
        print(error_msg)
        df.at[idx, 'fastHPOCR output'] = error_msg

# Save results
output_path = 'clinphen_check_output_with_hpo.xlsx'
df.to_excel(output_path, index=False)
print(f"\nProcessing complete! Results saved to: {output_path}")
print(f"Total processed rows: {len(df)}")