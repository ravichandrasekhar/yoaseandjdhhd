import requests
ACCESS_TOKEN=""
SHAREPOINT_SITE_ID=""
list_id = ""
def get_sharepoint_list_data(list_id):
    try:
        # Endpoint URL to retrieve the SharePoint list schema
        schema_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/columns"
        
        # Request headers
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }

        # Send GET request to retrieve the schema
        response = requests.get(schema_url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            schema_data = response.json()
            
            # Extract field names from the schema
            fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]
            print("Fields to expand and index:", fields_to_expand_and_index)

            # Construct the $select part of the URL
            select_fields = ','.join(fields_to_expand_and_index)
            # print("Select_field value:", select_fields)

            # Endpoint URL to retrieve items from a SharePoint list with expanded fields
            url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"

            # Send GET request to retrieve items with expanded fields
            response = requests.get(url, headers=headers)

            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                # print("Retrieved SharePoint data:", data)  # Print the retrieved data
                if 'value' in data:
                    return data['value']
                else:
                    print("No items found in the SharePoint list.")
                    return []
            else:
                print(f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
                return []
        else:
            print(f"Failed to retrieve schema from SharePoint list. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching data from SharePoint list: {str(e)}")
        return []
sh=get_sharepoint_list_data(list_id)
