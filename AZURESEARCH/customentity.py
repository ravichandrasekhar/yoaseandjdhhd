from azure.identity import DefaultAzureCredential
from azure.mgmt.search import SearchManagementClient
from azure.search.documents.indexes import CustomEntityRecognitionSkill, Skill, Skillset
import csv
# Azure subscription ID
subscription_id = '5f188abf-b04f-4b4a-8a4f-601c0a105543'

# Resource group name
resource_group_name = 'HudsonDDQQnA'

# Cognitive Search service name
search_service_name = 'ddqqna-astyx3pssxwxir2 '

# Existing Skillset name
existing_skillset_name = 'azureblob-skillset'

# Azure region where the Cognitive Search service is located
region = 'East US'

# Path to the file containing custom entities
file_path = "C:\\Users\\ravichandrav\\Desktop\\csv\\Book1.csv"

# Load custom entities from file
def load_custom_entities_from_csv(file_path):
    custom_entities = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            custom_entities.extend(row)
    return custom_entities


# Function to create custom entity recognition skill
def create_custom_entity_skill(skill_name, endpoint_url, custom_entities):
    custom_entity_skill = CustomEntityRecognitionSkill(
        name=skill_name,
        description='Custom Entity Recognition Skill',
        context=None,
        inputs=custom_entities,
        outputs=[],
        uri=endpoint_url
    )
    return custom_entity_skill

# Initialize Azure Management SDK client
credential = DefaultAzureCredential()
client = SearchManagementClient(credential, subscription_id)

# Retrieve the existing Skillset
skillset = client.skillsets.get(resource_group_name, search_service_name, existing_skillset_name)

# Load custom entities from file
custom_entities = load_custom_entities_from_csv(file_path)

# Azure Function endpoint URL
function_endpoint_url = 'https://demosample.azurewebsites.net'

# Create custom entity recognition skill
custom_entity_skill = create_custom_entity_skill('CustomEntityRecognitionSkill', function_endpoint_url, custom_entities)

# Add the custom entity recognition skill to the existing Skillset
skillset.skills.append(Skill(skill=custom_entity_skill))

# Update the Skillset
client.skillsets.create_or_update(resource_group_name, search_service_name, existing_skillset_name, skillset)

print(f"Custom entity recognition skill added to the Skillset '{existing_skillset_name}'.")
