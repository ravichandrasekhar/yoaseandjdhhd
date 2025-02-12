from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchFieldDataType, SearchIndex,SynonymMap, ComplexField, SearchableField

def upload_data_from_excel(file_path, index_client):
    import openpyxl

    workbook = openpyxl.load_workbook(file_path)
    worksheet = workbook.active

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        document = {
            "ProductID": row[0],
            "ProductName": row[1],
            "Description": row[2]
        }
        index_client.upload_documents(documents=[document])

def define_synonym_map(service_client):
    synonym_map = SynonymMap(
        name="products-synonyms",
        synonyms="Laptop, Notebook, Computer\nPhone, Mobile, Cellphone\nHeadphones, Earphones, Headset"
    )
    service_client.create_synonym_map(synonym_map)

def apply_synonyms_to_field(index_client):
    index = index_client.get_index()
    description_field = next((field for field in index.fields if field.name == "Description"), None)
    if description_field:
        description_field.synonym_map_names = ["products-synonyms"]
        index_client.create_or_update_index(fields=[description_field])

def main():
    # Azure Search service endpoint and API key
    service_endpoint = ""
    api_key = ""
    index_name = "sampleindex"

    # Path to the Excel file
    excel_file_path = "D:\\desktop\\csv\\sample.xlsx"

    # Create a SearchServiceClient
    service_client = SearchClient(service_endpoint, AzureKeyCredential(api_key))

    # Create an index client
    index_client = service_client.get_search_index_client(index_name)

    # Upload data from Excel file to Azure Search
    upload_data_from_excel(excel_file_path, index_client)

    # Define and create synonym map
    define_synonym_map(service_client)

    # Apply synonyms to the appropriate field
    apply_synonyms_to_field(index_client)

    print("Data uploaded and synonyms applied successfully!")

if __name__ == "__main__":
    main()
