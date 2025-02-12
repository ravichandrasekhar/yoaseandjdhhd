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

def get_all_sharepoint_drives(access_token, site_id):
    # Endpoint to get the default drive of the site
    endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get SharePoint drive: {response.text}")
        return None

# Obtain access token
access_token = get_access_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID)
print("Access Token:", access_token)

if access_token:
    all_sharepoint_drives = get_all_sharepoint_drives(access_token, SHAREPOINT_SITE_ID)
    if all_sharepoint_drives:
        print("All SharePoint Drives:")
        for drive in all_sharepoint_drives['value']:
            print("Drive ID:", drive['id'])
            print("Drive Name:", drive['name'])
            # print(drive)

            