import requests
SHAREPOINT_SITE_ID=""
ACCESS_TOKEN=""
group_id=""
page_id=""
def get_sharepoint_pages(SHAREPOINT_SITE_ID, ACCESS_TOKEN):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/pages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        print(f"Failed to retrieve SharePoint pages data: {response.text}")
        return []
sharepoint_pages = get_sharepoint_pages(SHAREPOINT_SITE_ID, ACCESS_TOKEN)
print("Sharepoint data",sharepoint_pages)
# Function to fetch group members
def get_group_members(group_id):
    try:
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/transitiveMembers/"
        group_members = []
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            members = response.json()["value"]

            for member in members:
                principal_name = member["userPrincipalName"]
                group_members.append(principal_name)

        return group_members
    except Exception as e:
        print(f"Error fetching group members for group {group_id}: {str(e)}")
        return []
    
groups = get_group_members(group_id)
print("Sharepoint data",groups)



import requests

def get_page_metadata(page_id):
    try:
        metadata_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/pages/{page_id}"
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(metadata_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching metadata for page {page_id}. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching metadata for page {page_id}: {str(e)}")
        return None

def get_page_permissions(page_metadata):
    try:
        permissions = []
        if page_metadata:
            page_permissions = page_metadata.get("permissions", [])
            for permission in page_permissions:
                granted_to = permission.get("grantedTo", None)
                if granted_to:
                    if "user" in granted_to:
                        user_or_group = granted_to["user"].get("displayName", "N/A")
                        permissions.append(user_or_group)
                    elif "group" in granted_to:
                        user_or_group = granted_to["group"].get("displayName", "N/A")
                        permissions.append(user_or_group)
        return permissions
    except Exception as e:
        print(f"Error parsing permissions for page: {str(e)}")
        return []

# Example usage

page_metadata = get_page_metadata(page_id)
if page_metadata:
    page_permissions = get_page_permissions(page_metadata)
    print("Page Permissions:", page_permissions)
