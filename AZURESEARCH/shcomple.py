import requests

def get_drive_id(site_url, access_token):
    # Extract hostname and site-relative path from the site URL
    parts = site_url.split('/')
    hostname = parts[2]  # This will be "mouritechpvtltd.sharepoint.com"
    site_path = '/'.join(parts[4:])  # This will be "sites/MTEnterpriseSearch"

    # Construct the Microsoft Graph API URL
    graph_url = f'https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}'
    print("Graph URL:", graph_url)

    # Headers with authorization
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    # Send GET request to retrieve site information
    response = requests.get(graph_url, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        site_info = response.json()
        site_id = site_info['id']
        print("Site ID:", site_id)
        
        # Construct the URL to get drives
        drive_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        print("Drive endpoint:", drive_endpoint)
        drive_response = requests.get(drive_endpoint, headers=headers)

        if drive_response.status_code == 200:
            drives_data = drive_response.json()["value"]
            if drives_data:
                # Print all drive IDs
                for drive in drives_data:
                    drive_id = drive["id"]
                    print("Drive ID:", drive_id)
                return drives_data  # Return all drive data
            else:
                print("No drives found.")
                return None
        else:
            print("Failed to retrieve drives information:", drive_response.text)
            return None
    else:
        print("Failed to retrieve site information:", response.text)
        return None

# Example usage
site_url = ""
access_token = ""
drive_data = get_drive_id(site_url, access_token)
def get_sharepoint_items(access_token, folder_id, SHAREPOINT_DRIVE_ID):
    try:
        if folder_id:
            url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/items/{folder_id}/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{SHAREPOINT_DRIVE_ID}/root/children"

        headers = {
            "Authorization": "Bearer " + access_token,
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data['value']
        else:
            print("Failed to retrieve items from SharePoint drive.", response.text)
    except Exception as e:
         print(f"Error fetching items from SharePoint drive: {str(e)}")


