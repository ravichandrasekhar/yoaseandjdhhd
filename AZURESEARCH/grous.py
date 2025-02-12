
import requests
# Define your client ID, client secret, and tenant ID for Azure Active Directory
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = "" 
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

access_token= get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)
# Endpoint URL
url = f'https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/groups'

# Set up headers, including the Authorization header with the access token
headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json'
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    groups = response.json()
    # Print the groups
    print(groups)
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)