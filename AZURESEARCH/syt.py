import requests
# Constants
SHAREPOINT_SITE_ID = ""
ACCESS_TOKEN = ""
list_id = ""
def get_sharepoint_list_data(list_id):
    try:
        # Define the fields to be expanded and indexed
        fields_to_expand_and_index = ["EntryID", "_x0048_1", "_x0048_2", "_x0048_3", "_x0048_4", "Content", "FileName"]

        # Construct the $select part of the URL
        select_fields = ','.join(fields_to_expand_and_index)
        print("Select_field value:", select_fields)

        # Endpoint URL to retrieve items from a SharePoint list with expanded fields
        url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{list_id}/items?expand=fields(select={select_fields})"
        print("stey:",url)
        # Request headers
        headers = {
            "Authorization": "Bearer " + ACCESS_TOKEN,
            "Accept": "application/json"
        }

        # Send GET request
        response = requests.get(url, headers=headers)

        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
             # Print the retrieved data
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
st=get_sharepoint_list_data(list_id)
