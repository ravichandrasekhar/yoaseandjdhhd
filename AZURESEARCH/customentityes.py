from azure.search.documents.indexes.models import (SearchIndex, 
                                                    SearchIndexerSkillset,
                                                    SearchIndexerSkill,
                                                    InputFieldMappingEntry,
                                                    OutputFieldMappingEntry)
from azure.search.documents.indexes import SearchIndexerClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

def create_skillset():
    # Azure Cognitive Search service endpoint
    endpoint = ""
    
    # Admin API key for the Azure Cognitive Search service
    key = ""
    
    # Name of the skillset
    skillset_name = "azureblob-skillset"
    
    # Endpoint URL of your Azure Function containing the custom skill
    function_endpoint = "https://demosample.azurewebsites.net"
    
    # Initialize the SearchIndexerClient
    search_client = SearchIndexerClient(endpoint, AzureKeyCredential(key))
    
    # Define the custom skill
    custom_skill = {
        "@odata.type": "#Microsoft.Skills.CustomEntityLookupSkill",
        "name": "CustomSkill",
        "description": "Custom Skill for CSV Lookup",
        "uri": function_endpoint,
        "httpMethod": "POST",
        "timeout": "PT30S",
        "context": "/document",
        "batchSize": 1,
        "inputs": [
            {
                "name": "content",
                "source": "/document/content"
            }
        ],
        "outputs": [
            {
                "name": "extracted_terms",
                "targetName": "extracted_terms"
            }
        ]
    }
    
    # Create the skillset
    try:
        skillset = search_client.create_skillset(skillset_name, skills=[custom_skill])
        print("Skillset created successfully.")
    except HttpResponseError as e:
        print("Skillset creation failed:")
        print(e)

# Call the function to create the skillset
create_skillset()
