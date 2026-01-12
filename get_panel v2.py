#Part 1 download gene panels
import requests
import json
import pandas as pd
from datetime import datetime
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

#Need to manually provide url for query
uk_urls = [
    "https://panelapp.genomicsengland.co.uk/api/v1/panels/",
    "https://panelapp.genomicsengland.co.uk/api/v1/panels/?page=2",
    "https://panelapp.genomicsengland.co.uk/api/v1/panels/?page=3",
    "https://panelapp.genomicsengland.co.uk/api/v1/panels/?page=4",
    "https://panelapp.genomicsengland.co.uk/api/v1/panels/?page=5"
]

aus_urls = [
    "https://panelapp.agha.umccr.org/api/v1/panels/",
    "https://panelapp.agha.umccr.org/api/v1/panels/?page=2",
    "https://panelapp.agha.umccr.org/api/v1/panels/?page=3"
]

def query_panelapp_api(url):
    response = requests.get(url)
    return response.json()

def fetch(urls):
    all_data = {
        "count": 0,
        "results": []
    }
    for i, url in enumerate(urls):
        data = query_panelapp_api(url)
        if i == 0:  
            all_data["count"] = data['count']
        all_data["results"].extend(data['results'])
    return all_data

uk_data = fetch(uk_urls)
aus_data = fetch(aus_urls)


def create_dataframe(data):
    df = pd.DataFrame(data['results'])
    #df = df[['name', 'disease_group', 'disease_sub_group']]
    return df

#with open(f'panelapp_uk_response_{timestamp}.json', 'w') as file:
#    json.dump(uk_data, file, indent=4)

#with open(f'panelapp_aus_response_{timestamp}.json', 'w') as file:
#    json.dump(aus_data, file, indent=4)

uk_df = create_dataframe(uk_data)
aus_df = create_dataframe(aus_data)

with pd.ExcelWriter(f'merged_gene_panel.xlsx') as writer:
    uk_df.to_excel(writer, sheet_name="uk_panel", index=False)
    aus_df.to_excel(writer, sheet_name='aus_panel', index=False)
 
 
 
################################
#Part 2 generate moi dict
#Please open the merged_gene_panel.xlsx generated in part I, and delete the rows that are not interested and use it as an input.
import requests
import pandas as pd
import json
from datetime import datetime
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

indf = pd.read_excel('C:/Users/dlhyeung/Downloads/indf.xlsx', sheet_name=None)

def query_panel_details(panel_id, base_url):
    url = f"{base_url}/{panel_id}/"
    response = requests.get(url)
    if response.status_code == 200:
        #print(response.json())
        return response.json()
    else:
        return None

base_urls = {
    "uk": "https://panelapp.genomicsengland.co.uk/api/v1/panels",
    "aus": "https://panelapp.agha.umccr.org/api/v1/panels" }
detailed_panels = {"uk": [], "aus": []}

for sheet_name, df in indf.items():
    source = "uk" if "uk" in sheet_name else "aus"
    for panel_id in df['id']:
        panel_data = query_panel_details(panel_id, base_urls[source])
        if panel_data:
            detailed_panels[source].append(panel_data)


# Save detailed panel data to JSON files
#with open(f'panelapp_uk_details_{timestamp}.json', 'w') as file:
#    json.dump(detailed_panels['uk'], file, indent=4)
#with open(f'panelapp_aus_details_{timestamp}.json', 'w') as file:
#    json.dump(detailed_panels['aus'], file, indent=4)
    
def parse_gene_info(panel_data):
    rows = []
    for panel in panel_data:
        panel_name = panel['name']
        for gene in panel['genes']:
            confidence_level = gene.get('confidence_level', None)
            if confidence_level in ['2', '3']:
                gene_symbol = gene['gene_data']['gene_symbol']
                moi = gene.get('mode_of_inheritance', 'N/A')
                if 'BOTH monoallelic and biallelic' in moi:
                    ad_listed = 'y'
                    ar_listed = 'y'
                else:
                    ad_listed = 'y' if 'MONOALLELIC' in moi else ''
                    ar_listed = 'y' if 'BIALLELIC' in moi else ''
                xl_listed = 'y' if 'X-LINKED' in moi else ''
                unknown = 'y' if 'Unknown' in moi else ''
                rows.append({
                    "panel name": panel_name,
                    "gene": gene_symbol,
                    "moi": moi,
                    "in AD genelist?": ad_listed,
                    "in AR genelist?": ar_listed,
                    "in XL genelist?": xl_listed,
                    'unknown':unknown
                })
    return rows

uk_gene_info = parse_gene_info(detailed_panels['uk'])
aus_gene_info = parse_gene_info(detailed_panels['aus'])

uk_gene_df = pd.DataFrame(uk_gene_info)
aus_gene_df = pd.DataFrame(aus_gene_info)





def parse_gene_info_with_version(panel_data, source_tag):
    rows = []
    for panel in panel_data:
        panel_name = panel['name']
        panel_version = panel['version']
        gene_list = []
        for gene in panel['genes']:
            confidence_level = gene.get('confidence_level', None)
            if confidence_level in ['2', '3']:  # Amber (2) or Green (3)
                gene_symbol = gene['gene_data']['gene_symbol']
                gene_list.append(gene_symbol)
        if gene_list:
            rows.append({
                "panel_name_version": f"({source_tag}) {panel_name} v{panel_version}",
                "gene_list": ", ".join(gene_list)
            })
    return rows

# Parse gene information for both UK and AUS panels
uk_gene_info = parse_gene_info_with_version(detailed_panels['uk'], "uk")
aus_gene_info = parse_gene_info_with_version(detailed_panels['aus'], "au")

uk_gene_df = pd.DataFrame(uk_gene_info)
aus_gene_df = pd.DataFrame(aus_gene_info)
# Combine UK and AUS DataFrames into one
merged_gene_df = pd.concat([uk_gene_df, aus_gene_df], ignore_index=True)

# Save the merged output to a CSV file
merged_gene_df.to_csv("geneyx_gene_panels.csv", index=False)

print("Merged file saved as 'merged_panel_genes.csv'")












with pd.ExcelWriter(f'merged_gene_summary_df_{timestamp}.xlsx') as writer:
    uk_gene_df.to_excel(writer, sheet_name="uk_summary", index=False)
    aus_gene_df.to_excel(writer, sheet_name='aus_summary', index=False)






def create_summary_table(gene_df):
    summary_data = {}
    for _, row in gene_df.iterrows():
        gene = row['gene']
        moi = row['moi']
        if gene not in summary_data:
            summary_data[gene] = set()
        if 'BOTH monoallelic and biallelic' in moi:
            summary_data[gene].add('AD')
            summary_data[gene].add('AR')
        if 'MONOALLELIC' in moi:
            summary_data[gene].add('AD')
        if 'BIALLELIC' in moi:
            summary_data[gene].add('AR')
        if 'X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)' in moi:
            summary_data[gene].add('XLD')
        if 'X-LINKED: hemizygous mutation in males, biallelic mutations in females' in moi:
            summary_data[gene].add('XLR')
    summary_rows = []
    for gene, mois in summary_data.items():
        summary_rows.append({
            "gene_symbol": gene,
            "moi": "/".join(sorted(mois))
        })
    summary_df = pd.DataFrame(summary_rows)
    return summary_df

uk_summary_df = create_summary_table(uk_gene_df)
aus_summary_df = create_summary_table(aus_gene_df)

with pd.ExcelWriter(f'merged_summary_df_{timestamp}.xlsx') as writer:
    uk_summary_df.to_excel(writer, sheet_name="uk_summary_df", index=False)
    aus_summary_df.to_excel(writer, sheet_name='aus_summary_df', index=False)

merged_df = pd.merge(uk_summary_df, aus_summary_df, on='gene_symbol', how='outer', suffixes=('_uk', '_aus'))

def combine_moi(row):
    moi_uk = row['moi_uk']
    moi_aus = row['moi_aus']
    combined = set()
    if pd.notna(moi_uk) and moi_uk != 'Unknown':
        combined.update(filter(None, moi_uk.split('/')))
    if pd.notna(moi_aus) and moi_aus != 'Unknown':
        combined.update(filter(None, moi_aus.split('/')))
    if not combined:
        return 'Unknown'
    return '/'.join(sorted(combined))

merged_df['moi_for_bespoke'] = merged_df.apply(combine_moi, axis=1)
merged_df.to_csv(f'moi_dict.csv',index=False)

final_df = merged_df[['gene_symbol', 'moi_for_bespoke']]
final_df.to_csv(f'merged_moi_dict.csv',index=False)