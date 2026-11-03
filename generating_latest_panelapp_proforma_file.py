import requests
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_panels(base_url, headers, max_panels=10):
    """Fetch all available panels with pagination and optional limit."""
    panels = []
    url = f'{base_url}/panels/'
    panel_count = 0
    print("Starting to fetch panel data...")
    while url:
        print(f"Fetching panel list from: {url}")
        response = requests.get(url, headers=headers)
        try:
            data = response.json()
        except Exception as e:
            print(f"Failed to parse JSON from URL: {url}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Content:\n{response.text}\n")
            raise e
        panels.extend(data['results'])
        panel_count += len(data['results'])
        print(f"Retrieved {len(data['results'])} panels. Total panels so far: {panel_count}")
        url = data['next']
        if max_panels and panel_count >= max_panels:
            print(f"Reached the max panels limit of {max_panels}.")
            break
        #time.sleep(1)  # Adding delay to avoid potential rate-limiting
    return panels[:max_panels] if max_panels else panels

def get_panel_details(base_url, panel_id, headers):
    """Fetch detailed information for a single panel."""
    url = f'{base_url}/panels/{panel_id}/'
    print(f"Fetching details for panel ID: {panel_id}")
    response = requests.get(url, headers=headers)
    try:
        panel_data = response.json()
    except Exception as e:
        print(f"Failed to parse JSON from URL: {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Response Content:\n{response.text}\n")
        raise e
    print(f"Successfully retrieved details for panel ID: {panel_id}")
    print(panel_data)
    return panel_data

def process_panel_data(panel, base_url, headers, country_code, confidence_level_map):
    """Process data for a single panel and return formatted gene information."""
    panel_id = panel['id']
    panel_name = panel['name']
    panel_version = panel['version']
    
    panel_details = get_panel_details(base_url, panel_id, headers)
    genes = panel_details.get('genes', [])
    
    data_list = []
    print(f"Processing {len(genes)} genes for panel: {panel_name} (ID: {panel_id})")
    for gene_entry in genes:
        gene_symbol = gene_entry['gene_data']['gene_symbol']
        gene_class = 'gene'
        
        # Retrieve confidence level for the gene, default to Green if missing
        confidence_level_int = gene_entry.get('confidence_level', 3)  # Default to 3 (Green)
        confidence_level = confidence_level_map.get(confidence_level_int, 'Green')
        
        # Formulate id, name, and other columns
        id_str = f'panel{country_code}_{panel_id}'
        name_str = f'({country_code}){panel_name} {panel_version}'
        
        evidence = f'{confidence_level},'
        proforma = f'{panel_name} (V{panel_version}), {confidence_level}'
        
        data_list.append({
            'id': id_str,
            'name': name_str,
            'gene': gene_symbol,
            'class': gene_class,
            'evidence': evidence,
            'proforma': proforma
        })
    
    return data_list
# Define the confidence level map

def process_panel_data(panel, base_url, headers, country_code, confidence_level_map):
    """Process data for a single panel and return formatted gene information, only including Green and Amber genes."""
    panel_id = panel['id']
    panel_name = panel['name']
    panel_version = panel['version']
    
    panel_details = get_panel_details(base_url, panel_id, headers)
    genes = panel_details.get('genes', [])
    
    data_list = []
    print(f"Processing {len(genes)} genes for panel: {panel_name} (ID: {panel_id})")
    for gene_entry in genes:
        gene_symbol = gene_entry['gene_data']['gene_symbol']
        gene_class = 'gene'
        
        # Retrieve confidence level as a string and filter only for '2' (Amber) and '3' (Green)
        confidence_level_str = gene_entry['confidence_level']
        
        if confidence_level_str in ["2", "3"]:  # Only include Amber and Green genes
            confidence_level = confidence_level_map[int(confidence_level_str)]
            
            # Formulate id, name, and other columns
            id_str = f'panel{country_code}_{panel_id}'
            name_str = f'({country_code}){panel_name} {panel_version}'
            
            evidence = f'{confidence_level},'
            proforma = f'{panel_name} (V{panel_version}), {confidence_level}'
            
            data_list.append({
                'id': id_str,
                'name': name_str,
                'gene': gene_symbol,
                'class': gene_class,
                'evidence': evidence,
                'proforma': proforma
            })
        
    return data_list




def process_panels(base_url, country_code, headers, max_panels=None):
    """Process all panels and extract relevant gene information concurrently."""
    print(f"Processing panels from {country_code.upper()}...")
    panels = get_panels(base_url, headers, max_panels)
    confidence_level_map = {
        3: 'Green',
        2: 'Amber',
        1: 'Red',
        0: 'No List'
    }

    # Parallel processing using ThreadPoolExecutor
    all_gene_data = []
    with ThreadPoolExecutor(max_workers=20) as executor:  # Adjust max_workers as needed
        future_to_panel = {
            executor.submit(process_panel_data, panel, base_url, headers, country_code, confidence_level_map): panel 
            for panel in panels
        }
        for future in as_completed(future_to_panel):
            panel = future_to_panel[future]
            try:
                data_list = future.result()
                all_gene_data.extend(data_list)
                print(f"Completed processing for panel ID: {panel['id']}")
            except Exception as e:
                print(f"Error processing panel ID {panel['id']}: {e}")

    # Create dataframe from combined gene data
    df = pd.DataFrame(all_gene_data)
    print(f"Completed processing {len(all_gene_data)} gene entries for {country_code.upper()}.")
    return df

def main():
    uk_base_url = 'https://panelapp.genomicsengland.co.uk/api/v1'
    aus_base_url = 'https://panelapp-aus.org/api/v1'
    # Define headers (Update with actual API key if required)
    headers = {
        'Accept': 'application/json',
    }

    # Process UK panels
    print("Processing UK panels...")
    uk_df = process_panels(uk_base_url, 'uk', headers, max_panels=None)  # Adjust max_panels as needed
    uk_output_file = 'uk_panels.xlsx'
    uk_df.to_excel(uk_output_file, index=False)
    print(f"UK panels data saved to {uk_output_file}.")

    # Process Australian panels
    print("Processing Australian panels...")
    aus_df = process_panels(aus_base_url, 'aus', headers, max_panels=None)  # Adjust max_panels as needed
    aus_output_file = 'aus_panels.xlsx'
    aus_df.to_excel(aus_output_file, index=False)
    print(f"Australian panels data saved to {aus_output_file}.")
    output_file = 'combined_panel.xlsx'
    with pd.ExcelWriter(output_file) as writer:
        uk_df.to_excel(writer, sheet_name='uk', index=False)
        aus_df.to_excel(writer, sheet_name='aus', index=False)
    print(f"Combined panel data saved to {output_file} with sheets 'uk' and 'aus'.")


if __name__ == '__main__':
    main()
