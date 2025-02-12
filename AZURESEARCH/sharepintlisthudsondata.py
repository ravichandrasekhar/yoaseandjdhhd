import requests
import json
# # Define your client ID and client secret
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = ""  # This is usually in the form of a GUID

SHAREPOINT_SITE_ID = ""
SHAREPOINT_LIST_ID = ""

def get_access_token(client_id, client_secret, tenant_id):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to retrieve access token: {response.text}")
        return None
access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)
def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)

def get_sharepoint_list_data(site_id, list_id, access_token):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{SHAREPOINT_LIST_ID}/items"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        print(f"Failed to retrieve SharePoint list data: {response.text}")
        return []

# # Retrieve access token
# access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)

# Retrieve SharePoint list data
sharepoint_list_data = get_sharepoint_list_data(SHAREPOINT_SITE_ID, SHAREPOINT_LIST_ID, access_token)
print("SharePoint List Data:", sharepoint_list_data)
# Save SharePoint lists data to a JSON file
save_to_json(sharepoint_list_data, 'sharepoint_listssss.json')
def get_sharepoint_list_data1(SHAREPOINT_LIST_ID,access_token):
    try:
   
        # Endpoint URL to retrieve items from a SharePoint list with expanded fields
        url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{SHAREPOINT_LIST_ID}/items?expand=fields"

        # Request headers
        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }

        # Send GET request
        response = requests.get(url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            print("Retrieved SharePoint data:", data)  # Print the retrieved data
            if 'value' in data:
                return data['value']
            else:
                print("No items found in the SharePoint list.")
                return []
        else:
            print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return []
sharepoint_list_data1 = get_sharepoint_list_data1(SHAREPOINT_LIST_ID, access_token)
print("SharePoint List Data:", sharepoint_list_data1)
save_to_json(sharepoint_list_data, 'sharepoint_lists1.json')

def get_sharepoint_list_schema(site_id, list_id, access_token):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        schema = response.json().get("value", [])
        field_names = [field["name"] for field in schema]
        return field_names
    else:
        print(f"Failed to retrieve SharePoint list schema: {response.text}")
        return []



# Retrieve SharePoint list schema
field_names = get_sharepoint_list_schema(SHAREPOINT_SITE_ID, SHAREPOINT_LIST_ID, access_token)
print("Available Fields:", field_names)

# Construct expand query dynamically
select_fields = ",".join(field_names)
expand_query = f"fields(select={select_fields})"

def get_sharepoint_items_with_expand(site_id, list_id, access_token, expand_query):
    items_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand={expand_query}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(items_url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("value", [])
        return items
    else:
        print(f"Failed to retrieve items: {response.text}")
        return []

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Retrieve access token


# Construct expand query dynamically
expand_query = "fields"

# Get SharePoint items with all fields expanded
items = get_sharepoint_items_with_expand(SHAREPOINT_SITE_ID, SHAREPOINT_LIST_ID, access_token, expand_query)

# Save SharePoint items to a JSON file
save_to_json(items, 'sharepoint_items1.json')

