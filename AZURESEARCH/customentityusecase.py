import csv
import json
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchServiceClient
# Define your Azure Cognitive Search details
endpoint = ""
index_name = "azureblob-index"
skillset_name = "azureblob-skillset"
function_url = ""
entities_file = "C:\\Users\\ravichandrav\\Desktop\\csv\\Book1.csv"  # Path to your sample CSV file
def custom_entity_lookup(text):
    # Define your custom entities and their associated values
    custom_entities = {}
    with open("custom_entities.csv", "r", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            entity, entity_type = row
            custom_entities[entity] = entity_type

    # Process the text
    entities = []
    for entity, entity_type in custom_entities.items():
        if entity in text:
            entities.append({"entity": entity, "entityType": entity_type})
    return entities

def main(req: func.HttpRequest) -> func.HttpResponse:

    # Retrieve the text from the request body
    req_body = req.get_json()
    text = req_body.get('text') if req_body else None

    if text:
        # Perform custom entity lookup
        entities = custom_entity_lookup(text)
        return func.HttpResponse(body=json.dumps(entities), mimetype="application/json")
    else:
        return func.HttpResponse(
             "Please pass text in the request body",
             status_code=400
        )

# Initialize the Azure Cognitive Search client
credential = DefaultAzureCredential()
client = SearchServiceClient(endpoint=endpoint, credential=credential)

# Retrieve the existing skillset
skillset = client.skillsets.get(index_name, skillset_name)

# Define the custom skill
custom_skill = {
    "description": "Custom entity lookup skill",
    "@odata.type": "#Microsoft.Skills.CustomEntityLookupSkill",
    "name": "custom-entity-lookup",
    "context": "/document",
    "inputs": [
        {
            "name": "text",
            "source": "/document/your_text_field"  # Change 'your_text_field' to the actual field containing text
        }
    ],
    "outputs": [
        {
            "name": "entities",
            "targetName": "entities"
        }
    ],
    "uri": function_url
}

# Add the custom skill to the skillset
skillset.skills.append(custom_skill)

# Define the key field
key_field = {
    "name": "your_key_field",  # Change 'your_key_field' to the actual key field name
    "type": "Edm.String",
    "key": True
}

# Add the key field to the skillset if it doesn't exist
if not any(field['name'] == key_field['name'] for field in skillset.fields):
    skillset.fields.append(key_field)

# Update the skillset
client.skillsets.create_or_update(index_name, skillset_name, skillset)
