import pandas as pd
import re
from typing import Set, Dict

SHEET_NAME = '30_testing_cases_20251210'
PREDICTION_COLUMNS = ['Clinphen', 'fastHPOCR', 'Phenotagger', 'RAG-HPO', 'qwen + fastHPOCR']
GOLD_STANDARD_COLUMN = 'Maunal input HPO'

def extract_hpo_ids(text: str) -> Set[str]:
    if pd.isna(text) or not isinstance(text, str):
        return set()
    return set(re.findall(r'HP:\d{7}', text, re.IGNORECASE))

def calculate_metrics(gold_standard: Set[str], prediction: Set[str]) -> Dict[str, float]:
    if not gold_standard and not prediction:
        return {'TP': 0, 'FP': 0, 'FN': 0, 'Precision': 1.0, 'Recall': 1.0, 'F1': 1.0}
    
    tp = len(gold_standard & prediction)
    fp = len(prediction - gold_standard)
    fn = len(gold_standard - prediction)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'TP': tp,
        'FP': fp,
        'FN': fn,
        'Precision': round(precision, 2),
        'Recall': round(recall, 2),
        'F1': round(f1, 2)
    }

def generate_evaluation(input_file: str, output_file: str):
    df = pd.read_excel(input_file, sheet_name=SHEET_NAME)
    df['Gold_Standard_HPO_Set'] = df[GOLD_STANDARD_COLUMN].apply(extract_hpo_ids)
    
    # Create per-case evaluation sheet
    all_results = []
    for _, row in df.iterrows():
        case_id = row['Ref_ID']
        gt_set = row['Gold_Standard_HPO_Set']
        
        for tool in PREDICTION_COLUMNS:
            pred_set = extract_hpo_ids(str(row[tool]))
            metrics = calculate_metrics(gt_set, pred_set)
            
            result = {
                'Patient ID': case_id,
                'Tool': tool,
                **metrics
            }
            all_results.append(result)
    
    results_df = pd.DataFrame(all_results)
    
    wide_df = results_df.pivot(index='Patient ID', columns='Tool', values=['TP', 'FP', 'FN', 'Precision', 'Recall', 'F1'])
    wide_df.columns = [f'{tool}_{metric}' for metric, tool in wide_df.columns]
    wide_df = wide_df.reset_index()
    
    # Reorder columns
    ordered_cols = ['Patient ID']
    for tool in PREDICTION_COLUMNS:
        for metric in ['TP', 'FP', 'FN', 'Precision', 'Recall', 'F1']:
            ordered_cols.append(f'{tool}_{metric}')
    wide_df = wide_df[ordered_cols]
    
    # Add overall row
    overall_row = {'Patient ID': 'Overall'}
    for tool in PREDICTION_COLUMNS:
        tool_data = results_df[results_df['Tool'] == tool]
        total_tp = tool_data['TP'].sum()
        total_fp = tool_data['FP'].sum()
        total_fn = tool_data['FN'].sum()
        
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        overall_row[f'{tool}_TP'] = int(total_tp)
        overall_row[f'{tool}_FP'] = int(total_fp)
        overall_row[f'{tool}_FN'] = int(total_fn)
        overall_row[f'{tool}_Precision'] = round(precision, 2)
        overall_row[f'{tool}_Recall'] = round(recall, 2)
        overall_row[f'{tool}_F1'] = round(f1, 2)
    
    wide_df = pd.concat([wide_df, pd.DataFrame([overall_row])], ignore_index=True)
    
    # Create overall statistics sheet
    stats_df = results_df.groupby('Tool').agg(
        Avg_Precision=('Precision', 'mean'),
        Avg_Recall=('Recall', 'mean'),
        Avg_F1=('F1', 'mean')
    ).reset_index()
    
    stats_df = stats_df.round({
        'Avg_Precision': 2,
        'Avg_Recall': 2,
        'Avg_F1': 2
    })
    
    # Create validation checks sheet with new column
    validation_rows = []
    for _, row in df.iterrows():
        case_id = row['Ref_ID']
        gt_set = row['Gold_Standard_HPO_Set']
        clinical_summary = str(row['Clinical Summary'])[:150] + "..."  # Short preview
        
        # Get predictions from all tools
        tool_preds = {}
        for tool in PREDICTION_COLUMNS:
            tool_preds[tool] = extract_hpo_ids(str(row[tool]))
        
        # Initialize lists for different agreement levels
        two_tools_agree = []
        three_tools_agree = []
        four_tools_agree = []
        five_tools_agree = []
        missed_by_all = []
        missed_by_four_but_not_qwen = []  # New list for the requested column
        
        # Check all possible HPOs from tools and gold standard
        all_hpos = set()
        for preds in tool_preds.values():
            all_hpos.update(preds)
        all_hpos.update(gt_set)
        
        for hpo in all_hpos:
            # Count how many tools predicted this HPO
            tool_count = sum(1 for preds in tool_preds.values() if hpo in preds)
            
            # Case 1: Not in manual but agreed by tools
            if hpo not in gt_set:
                if tool_count == 2:
                    two_tools_agree.append(hpo)
                elif tool_count == 3:
                    three_tools_agree.append(hpo)
                elif tool_count == 4:
                    four_tools_agree.append(hpo)
                elif tool_count == 5:
                    five_tools_agree.append(hpo)
            
            # Case 2: In manual but missed by all tools
            elif tool_count == 0:
                missed_by_all.append(hpo)
        
        # Special case: In manual but missed by exactly 4 tools (only predicted by qwen+fastHPOCR)
        for hpo in gt_set:
            # Get tools that predicted this HPO
            predicting_tools = [tool for tool in PREDICTION_COLUMNS if hpo in tool_preds[tool]]
            # Check if only qwen+fastHPOCR predicted it and all others missed it
            if (len(predicting_tools) == 1 and 
                predicting_tools[0] == 'qwen + fastHPOCR' and
                len(PREDICTION_COLUMNS) - 1 == 4):  # Ensure there are exactly 4 other tools
                missed_by_four_but_not_qwen.append(hpo)
        
        validation_rows.append({
            'Case ID': case_id,
            'Clinical Summary Preview': clinical_summary,
            '2 tools agree but not in manual': ', '.join(sorted(two_tools_agree)),
            '3 tools agree but not in manual': ', '.join(sorted(three_tools_agree)),
            '4 tools agree but not in manual': ', '.join(sorted(four_tools_agree)),
            'All tools agree but not in manual': ', '.join(sorted(five_tools_agree)),
            'In manual but missed by all tools': ', '.join(sorted(missed_by_all)),
            'Missed by four but not qwen + fastHPOCR': ', '.join(sorted(missed_by_four_but_not_qwen))  # New column
        })
    
    validation_df = pd.DataFrame(validation_rows)
    
    # Save all sheets to new Excel file
    with pd.ExcelWriter(output_file) as writer:
        wide_df.to_excel(writer, sheet_name='Per_Case_Evaluation', index=False)
        stats_df.to_excel(writer, sheet_name='Overall_Statistics', index=False)
        validation_df.to_excel(writer, sheet_name='Validation_Checks', index=False)

# Usage
generate_evaluation("HPO_analysis.xlsx", "HPO_evaluation_results.xlsx")