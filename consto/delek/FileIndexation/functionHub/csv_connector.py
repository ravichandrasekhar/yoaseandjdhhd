import os
import uuid
import pandas as pd
import json
import logging
import azure.functions as func
from openai import AzureOpenAI
from FileIndexation.functionUtils.azure_index import AzureIndex


csv_connector = func.Blueprint()
# Environment variables for Azure OpenAI connection
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_NAME")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")

AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER")

AZURE_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")


# Initialize the OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_deployment=AZURE_OPENAI_EMBEDDING_NAME
)

def generate_embeddings(text):
    """Generate embeddings using Azure OpenAI."""
    try:
        response = client.embeddings.create(input=text, model=AZURE_OPENAI_EMBEDDING_NAME)
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"Error generating embeddings: {e}")
        raise


@csv_connector.route(route="csvIndexer")
def csvIndexer( req: func.HttpRequest) -> func.HttpResponse:

    azure_index = AzureIndex()
    if not azure_index.checkIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX):
        # If the index does not exist, create it
        azure_index.createIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)

    first_line_is_header=False
    sheet_name="delek technology cata"
    failure_count = 0
    try:
        # Retrieve filename from query params or request body
        file = req.files.get('file')

        # Determine file type based on content or extension (if provided)
        filename = file.filename
        file_content = file.read()
        file_extension = os.path.splitext(filename)[1].lower()

        skiprows = 1 if not first_line_is_header else 0
        
        processed_records = []

        # Handle CSV or Excel file based on the file extension
        if file_extension.endswith('.csv'):
            df = pd.read_csv(filename, skiprows=skiprows, encoding='windows-1252')
        else:
            df = pd.read_excel(file_content, sheet_name=sheet_name, header=None)

        # Normalize the column names to integers (0, 1, 2, ...)
        df.columns = [num for num in range(0, len(df.columns))]
        df = df[df[0].notna()]  # Remove rows where the first column is NaN

        column_names = [
            'Name', 'Subitems', 'Short Name (Acronym)', 'Description', 'Comments', 'Status', 
            'Candidate for Decommission', 'IT Application Owner', 'Business Owner', 'Application Portfolio Mgr',
            'Business Unit', 'Authentication Type', 'Lifecycle Stage', 'Business Criticality (Tier)', 
            'Business Process', 'Application Type', 'Application Platform', 'Architecture Type', 
            'Deployment Type', 'Install Type', 'Platform', 'Technology Stack', 'Application Version', 
            'Latest Available Version', 'User Base', 'In-Service Date', 'Out-of-Service Date', 'Support Group', 
            'Ticketing System', 'Vendor', 'Support Vendor', 'Contract End Date', 'Contract Term', 'Licensing', 
            'Cost Center', 'Cybersecurity Review Status', 'Data Classification', 'PCI Impact', 'SOX Impact', 
            'Upstream System (Source App)', 'Downstream System (Target App)', 'Data Integration', 'Database', 
            'Servers', 'Ports', 'Certificates', 'Certificates Start Date', 'Certificates End Date', 
            'DTC Record Valid', 'Item ID (auto generated)'
        ]
        
        # Convert DataFrame to JSON
        properties = json.loads(df.to_json(orient='records'))

        heading = ""
        for property in properties:
            try:
                # Skip records where the column values match the header names
                if list(property.values()) == column_names:
                    continue
                
                # If a certain field is missing or empty, treat it as a heading
                if property.get("5") is None or property.get("5") == "":
                    heading = property.get("0", "Unknown")
                    continue
                
                # Map DataFrame values to the expected column names
                row = {}
                for i in range(len(column_names)):
                    row[column_names[i]] = property.get(str(i), "")
                row["heading"] = heading
                processed_records.append(row)
                
            except Exception as ex:
                logging.exception(f"Error processing property: {ex}")
                failure_count += 1
            

            # Indexing the chunks
        for chunk_number, chunk in enumerate(processed_records,1):
        # for chunk in (processed_records):
            print("chunk",json.dumps(chunk))
            document = {
                "id": str(uuid.uuid4()),  # Generate unique I
                "content": json.dumps(chunk),
                "content_embeddings": [],  # Placeholder for embeddings
                "file_name": filename,
                "page_number": chunk_number,
                "application_name_embedding":''
            }
            # print(document)

            # Generate embeddings for the chunk
            document['application_name_embedding'] = generate_embeddings(chunk['Name'])
            document['content_embeddings'] = generate_embeddings(chunk)
            # print("document",document)

           
            try:
                azure_index.index_document_to_azure_search(document, AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)
            except Exception as e:
                logging.error(f"Error indexing document '{filename}', chunk {chunk_number}: {e}")

        logging.info("Files indexed successfully!")
        
        # Log the status and return the response
        logging.info(f"Processing completed with {failure_count} failures.")
        return func.HttpResponse(
            json.dumps({"status": "Success", "processed_records_count": json.dumps(processed_records)}),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as ex:
        logging.exception(f"An error occurred while processing the file: {ex}")
        return func.HttpResponse(
            json.dumps({"status": "Error", "message": str(ex)}),
            status_code=500,
            mimetype="application/json"
        )
    











# import os
# import uuid
# import pandas as pd
# import json
# import logging
# import azure.functions as func
# from openai import AzureOpenAI
# from FileIndexation.functionUtils.azure_index import AzureIndex


# csv_connector = func.Blueprint()
# # Environment variables for Azure OpenAI connection
# AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_EMBEDDING_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_NAME")
# AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION")

# AZURE_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
# AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
# AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")


# # Initialize the OpenAI client
# client = AzureOpenAI(
#     api_key=AZURE_OPENAI_KEY,
#     api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
#     azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     azure_deployment=AZURE_OPENAI_EMBEDDING_NAME
# )

# def generate_embeddings(text):
#     """Generate embeddings using Azure OpenAI."""
#     try:
#         response = client.embeddings.create(input=text, model=AZURE_OPENAI_EMBEDDING_NAME)
#         return response.data[0].embedding
#     except Exception as e:
#         logging.error(f"Error generating embeddings: {e}")
#         raise


# @csv_connector.route(route="csvIndexer")
# def csvIndexer( req: func.HttpRequest) -> func.HttpResponse:

#     azure_index = AzureIndex()
#     if not azure_index.checkIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX):
#         # If the index does not exist, create it
#         azure_index.createIndex(AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)

#     first_line_is_header=True
#     sheet_name="delek technology cata"
#     failure_count = 0
#     try:
#         # Retrieve filename from query params or request body
#         # file = req.files.get('file')

#         # Determine file type based on content or extension (if provided)
#         # filename = file.filename
#         filepath=r"D:\delekvinod\employees.csv"
#         filename= os.path.basename(filepath)
#         file_content=''
#         file_extension = os.path.splitext(filepath)[1].lower()

#         skiprows = 0 if not first_line_is_header else 0
        
#         processed_records = []

#         # Handle CSV or Excel file based on the file extension
#         if file_extension == '.csv':
#             df = pd.read_csv(filepath, skiprows=skiprows, encoding='windows-1252')
#         else:
#             df = pd.read_excel(file_content, sheet_name=sheet_name, header=None)

#         # Normalize the column names to integers (0, 1, 2, ...)
#         df.columns = [num for num in range(0, len(df.columns))]
#         # df = df[df[0].notna()]  # Remove rows where the first column is NaN

#         # Convert DataFrame to JSON
#         properties = json.loads(df.to_json(orient='records'))

#         # field_names=['client_id', 'company_name', 'contact_person', 'contact_email', 'contact_phone', 'address', 'industry', 'created_at', 'updated_at', 'skillrequired', 'skill_description']

#         field_names= [
#             "employee_id",
#             "first_name",
#             "last_name",
#             "email",
#             "phone_number",
#             "job_title",
#             "department_id",
#             "hire_date",
#             "manager_id",
#             "is_active",
#             "created_at",
#             "updated_at",
#             "Technical Skills",
#             "Professional experience"
#         ]

#         field_mapping = {str(i): field for i, field in enumerate(field_names)}


#             # Indexing the chunks
#         for chunk_number, chunk in enumerate(properties,1):
#             remapped_record = {field_mapping[key]: value for key, value in chunk.items() if key in field_mapping}

#         # for chunk in (processed_records):
#             # print("chunk",json.dumps(chunk))
#             document = {
#                 "id": str(uuid.uuid4()),  # Generate unique I
#                 "content":  json.dumps(remapped_record, indent=4),
#                 "content_embeddings": [],  # Placeholder for embeddings
#                 "file_name": filename,
#                 "page_number": chunk_number,
#                 # "entity_appName":chunk["Name"]
#             }
#             # print(document)

#             # Generate embeddings for the chunk
#             document['content_embeddings'] = generate_embeddings(chunk)
#             # print("document",document)

           
#             try:
#                 azure_index.index_document_to_azure_search(document, AZURE_SERVICE_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX)
#             except Exception as e:
#                 logging.error(f"Error indexing document '{filename}', chunk {chunk_number}: {e}")

#         logging.info("Files indexed successfully!")
        
#         # Log the status and return the response
#         logging.info(f"Processing completed with {failure_count} failures.")
#         return func.HttpResponse(
#             json.dumps({"status": "Success", "processed_records_count": json.dumps(processed_records)}),
#             status_code=200,
#             mimetype="application/json"
#         )
    
#     except Exception as ex:
#         logging.exception(f"An error occurred while processing the file: {ex}")
#         return func.HttpResponse(
#             json.dumps({"status": "Error", "message": str(ex)}),
#             status_code=500,
#             mimetype="application/json"
#         )