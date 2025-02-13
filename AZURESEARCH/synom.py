from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchableField, SearchFieldDataType, SynonymMap
import openpyxl
import requests
def upload_data_from_excel(file_path, search_client, index_name):
    workbook = openpyxl.load_workbook(file_path)
    worksheet = workbook.active

    actions = []
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        document = {
            "@search.action": "upload",
            "ProductID": str(row[0]),  # Assuming ProductID is a string
            "ProductName": row[1],
            "Description": row[2]
        }
        actions.append(document)

    # Upload documents to Azure Search
    result = search_client.upload_documents(documents=actions)
    if result[0].succeeded:
        print("Documents uploaded successfully!")
    else:
        print("Failed to upload documents:", result[0].errorMessage)

def create_index(service_endpoint, admin_key, index_name):
    # Define index schema
    index_fields = [
        SimpleField(name="ProductID", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True),
        SimpleField(name="ProductName", type=SearchFieldDataType.String),
        SearchableField(name="Description", type=SearchFieldDataType.String, searchable=True),
        
    ]
    index = SearchIndex(name=index_name, fields=index_fields)

    # Create index client
    index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(admin_key))

    try:
        # Check if the index exists
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating index...")
        # Create the index with the defined schema
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")
def define_synonym_map_through_api(endpoint, api_version, api_key):
    synonym_map_name = "products-synonyms"
    synonyms = "Laptop, Notebook, Computer\nPhone, Mobile, Cellphone, Mobilephone, Mobilepad\nHeadphones, Earphones, Headset"

    url = f"{endpoint}/synonymmaps?api-version={api_version}"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    data = {
        "name": synonym_map_name,
        "format": "solr",
        "synonyms": synonyms
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        print(f"Synonym map '{synonym_map_name}' has been created successfully.")
    else:
        print(f"Failed to create synonym map. Status code: {response.status_code}, Error: {response.text}")


        
def apply_synonyms_to_field(index_client):
    index_name = "sampleindex1"  # Replace with your actual index name
    index = index_client.get_index(index_name)
    
    # Find the Description field
    description_field = next((field for field in index.fields if field.name == "Description"), None)
    
    # Apply synonyms to the Description field if found
    if description_field:
        description_field.synonym_map_names = ["products-synonyms"]  # Add the synonym map name to the fiel
        index_client.create_or_update_index(index)  # Update the index with the modified field
    else:
        print("Description field not found in the index.")
        
def main():
    # Azure Search service endpoint, API key, and index name
    service_endpoint = ""
    admin_key = ""  # Replace with your actual admin ke
    index_name = ""  # Make sure this is the correct index name
    api_version="2020-06-30"
    # Create or update the index
    create_index(service_endpoint, admin_key, index_name)

    # Create a SearchClient with AzureKeyCredential
    credential = AzureKeyCredential(admin_key)
    search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)
    index_client = SearchIndexClient(endpoint=service_endpoint, credential=credential)

    # Path to the Excel file
    excel_file_path = "D:\\desktop\\csv\\sample.xlsx"

    # Upload data from Excel file to Azure Search
    upload_data_from_excel(excel_file_path, search_client, index_name)

    # Define and create synonym map
    define_synonym_map_through_api(service_endpoint, api_version, admin_key)

    # Apply synonyms to the appropriate field
    apply_synonyms_to_field(index_client)

    print("Data uploaded successfully!")

if __name__ == "__main__":
    main()