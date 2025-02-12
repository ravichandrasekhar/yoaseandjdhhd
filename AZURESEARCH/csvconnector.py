from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SimpleField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchIndex
)
import pandas as pd
import os

# Function to create index
def create_index(service_endpoint, admin_key, index_name, column_names, key_field_name):
    # Dynamically generate index fields based on column names
    index_fields = [
        SimpleField(name=str(column.replace(' ', '_')), type="Edm.String", key=(column == key_field_name)) for column in column_names
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
    )
    
    index_client = SearchIndexClient(endpoint=service_endpoint, credential=AzureKeyCredential(admin_key))
    
    # Create an instance of SearchIndex
    index = SearchIndex(
        name=index_name,
        fields=index_fields,
        vector_search=vector_search
    )
    
    try:
        existing_index = index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating index...")
        index_client.create_index(index)
        print(f"Index '{index_name}' has been created successfully.")

# Function to load data based on file extension
def load_data(csv_path):
    ext = os.path.splitext(csv_path)[-1].lower()
    if ext == '.csv':
        return pd.read_csv(csv_path)
    elif ext in ['.xlsx', '.xls']:
        return pd.read_excel(csv_path)
    else:
        raise ValueError("Unsupported file format. Only .csv, .xlsx, and .xls are supported.")

# Set up Azure Search client
endpoint = ""
index_name = "csvfile"
api_key = ""

# Load data
path = r"C:\Users\ravichandrav\Downloads\file_example_XLSX_100.xlsx"
df = load_data(path)

# Replace spaces in column names with underscores
df.columns = df.columns.str.replace(' ', '_')

# Get column names from the data
column_names = df.columns.tolist()

# Set the field to be used as the key
key_field_name = "id"  # Replace with the name of the field you want to use as the key

# Convert integer and float fields to strings
for col in df.select_dtypes(include=['int64', 'float64']).columns:
    df[col] = df[col].astype(str)

# Create index if not exists
create_index(endpoint, api_key, index_name, column_names, key_field_name)

# Set up Azure Search client after creating index
search_client = SearchClient(endpoint=endpoint, credential=AzureKeyCredential(api_key), index_name=index_name)

# Convert DataFrame to list of documents
documents = df.to_dict(orient='records')

# Index documents
search_client.upload_documents(documents=documents)

# Print IDs of uploaded documents
for document in documents:
    print(f"ID: {document[key_field_name]}")

print("Upload of documents succeeded.")
