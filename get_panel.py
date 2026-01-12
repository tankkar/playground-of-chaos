import requests
import json
import pandas as pd
from datetime import datetime


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

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

with open(f'panelapp_uk_response_{timestamp}.json', 'w') as file:
    json.dump(uk_data, file, indent=4)

with open(f'panelapp_aus_response_{timestamp}.json', 'w') as file:
    json.dump(aus_data, file, indent=4)

uk_df.to_csv(f'uk_df_{timestamp}.csv', index=False)
aus_df.to_csv(f'aus_df_{timestamp}.csv', index=False)