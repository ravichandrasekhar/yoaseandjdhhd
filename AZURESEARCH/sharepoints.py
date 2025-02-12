import requests
import json

SHAREPOINT_SITE_ID = ""
ACCESS_TOKEN = ""
GROUP_ID = ""

# Function to fetch SharePoint pages
def get_sharepoint_pages(SHAREPOINT_SITE_ID, ACCESS_TOKEN):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/pages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        pages = response.json().get("value", [])
        # Fetch content for each page
        for page in pages:
            page_id = page["id"]
            content_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/pages/{page_id}/content", headers=headers)
            if content_response.status_code == 200:
                page["content"] = content_response.json()
            else:
                page["content"] = None
        return pages
    else:
        print(f"Failed to retrieve SharePoint pages data: {response.text}")
        return []

# Function to fetch group members
def get_group_members(group_id, ACCESS_TOKEN):
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

# Function to fetch SharePoint lists and their items
def get_sharepoint_lists(SHAREPOINT_SITE_ID, ACCESS_TOKEN):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        lists = response.json().get("value", [])
        # Fetch items for each list
        for lst in lists:
            list_id = lst["id"]
            items_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items", headers=headers)
            if items_response.status_code == 200:
                lst["items"] = items_response.json().get("value", [])
            else:
                lst["items"] = []
        return lists
    else:
        print(f"Failed to retrieve SharePoint lists data: {response.text}")
        return []

# Function to fetch SharePoint drive items and their content
def get_sharepoint_drive_items(SHAREPOINT_SITE_ID, ACCESS_TOKEN):
    graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root/children"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.get(graph_endpoint, headers=headers)
    if response.status_code == 200:
        drive_items = response.json().get("value", [])
        # Fetch content for each drive item
        for item in drive_items:
            item_id = item["id"]
            content_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/items/{item_id}", headers=headers)
            if content_response.status_code == 200:
                item["content"] = content_response.json()
            else:
                item["content"] = None
        return drive_items
    else:
        print(f"Failed to retrieve SharePoint drive items data: {response.text}")
        return []

# Function to save data to a JSON file
def save_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Fetch and save SharePoint pages
sharepoint_pages = get_sharepoint_pages(SHAREPOINT_SITE_ID, ACCESS_TOKEN)
print("SharePoint Pages:", sharepoint_pages)
save_to_json(sharepoint_pages, 'sharepoint_pages.json')

# Fetch and save group members
group_members = get_group_members(GROUP_ID, ACCESS_TOKEN)
print("Group Members:", group_members)
save_to_json(group_members, 'group_members.json')

# Fetch and save SharePoint lists and their items
sharepoint_lists = get_sharepoint_lists(SHAREPOINT_SITE_ID, ACCESS_TOKEN)
print("SharePoint Lists:", sharepoint_lists)
save_to_json(sharepoint_lists, 'sharepoint_lists.json')

# Fetch and save SharePoint drive items and their content
sharepoint_drive_items = get_sharepoint_drive_items(SHAREPOINT_SITE_ID, ACCESS_TOKEN)
print("SharePoint Drive Items:", sharepoint_drive_items)
save_to_json(sharepoint_drive_items, 'sharepoint_drive_items.json')
