import requests

# Define your client ID and client secret
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = ""  # This is usually in the form of a GUID

# Define your SharePoint site ID
SHAREPOINT_SITE_ID = ""

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

def get_sharepoint_lists(site_id, access_token):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve SharePoint lists data: {response.text}")
        return []

# Retrieve access token
access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)

# Retrieve SharePoint lists
sharepoint_lists = get_sharepoint_lists(SHAREPOINT_SITE_ID, access_token)
print("SharePoint Lists:", sharepoint_lists)
