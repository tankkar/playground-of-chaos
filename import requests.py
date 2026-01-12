import requests

# Define the PanelApp API URL for panel ID 285
url = "https://panelapp.genomicsengland.co.uk/api/v1/panels/285/"

# Send a GET request to fetch the JSON data
response = requests.get(url)

# Check if the request was successful [[4]]
if response.status_code == 200:
    panel_data = response.json()
else:
    raise Exception(f"Failed to fetch data: {response.status_code}")


import json
with open('intellectual_disability_uk.json', 'w') as f:
    json.dump(panel_data, f, indent=4)