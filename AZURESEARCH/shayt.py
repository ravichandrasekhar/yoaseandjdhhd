import requests

ACCESS_TOKEN = ""
SHAREPOINT_SITE_ID = ""
# list_id=""
def get_sharepoint_list_data(list_id, ACCESS_TOKEN, SHAREPOINT_SITE_ID):
    try:
        schema_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/columns"
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(schema_url, headers=headers)
        if response.status_code == 200:
            schema_data = response.json()
            fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]


            select_fields = ','.join(fields_to_expand_and_index)
            url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'value' in data:
                    return data['value'], fields_to_expand_and_index
                else:
                    print("No items found in the SharePoint list.")
                    return [], []
            else:
                print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
                return [], []
        else:
            print(f"Failed to retrieve schema from SharePoint list. Status code: {response.status_code}")
            return [], []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return [], []

def get_all_sharepoint_lists(ACCESS_TOKEN, SHAREPOINT_SITE_ID):
    try:
        lists_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists"
        # print("retriveing list url {list_url}")
        print("sharepoint_site_id",SHAREPOINT_SITE_ID)
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }
        response = requests.get(lists_url, headers=headers)
        if response.status_code == 200:
            lists_data = response.json().get("value", [])
            all_lists_data = []
            for list_item in lists_data:
                list_id = list_item["id"]
                fields_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/columns"
                response = requests.get(fields_url, headers=headers)
                if response.status_code == 200:
                    schema_data = response.json()
                    fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]


                    select_fields = ','.join(fields_to_expand_and_index)
                    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if 'value' in data:
                            return data['value'], fields_to_expand_and_index
                        else:
                            print("No items found in the SharePoint list.")
                            return [], []
                    else:
                        print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
                        return [], []
                else:
                    print(f"Failed to retrieve schema from SharePoint list. Status code: {response.status_code}")
                    return [], []
            
            return all_lists_data
        else:
            print(f"Failed to retrieve lists from SharePoint site. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching lists from SharePoint site: {str(e)}")
        return []
all_lists_data = get_all_sharepoint_lists(ACCESS_TOKEN, SHAREPOINT_SITE_ID)
print("sg",all_lists_data)

# list_data=get_sharepoint_list_data(list_id, ACCESS_TOKEN, SHAREPOINT_SITE_ID)
# print("list_data",list_data)
