import csv
 
def read_customer_skill_entities(file_path):
  """
  This function reads customer skill entities and synonyms from a local CSV file.
 
  Args:
    file_path: The path to the CSV file containing skill entities.
 
  Returns:
    A dictionary where keys are entities and values are lists of synonyms.
  """
 
  skill_entities = {}
  with open(file_path, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
      entity = row['Entity'].lower()
      synonyms = [synonym.lower() for synonym in row['Synonyms'].split(', ')]
      skill_entities[entity] = synonyms
  return skill_entities
 
# Example usage
skill_entity_file = "C:\\Users\\ravichandrav\\Desktop\\csv\\sample.csv" # Replace with your actual file path
skill_definitions = read_customer_skill_entities(skill_entity_file)
 
print("Loaded customer skill entities:")
for entity, synonyms in skill_definitions.items():
  print(f"- {entity} ({', '.join(synonyms)})")