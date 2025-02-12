import re

# Define your regex patterns
regex_patterns = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email pattern
    'phone_number': r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'  # Phone number pattern
}

# Define your whitelist of terms or phrases
whitelist = {
    'company_names': ['Google', 'Apple', 'Microsoft'],
    'product_names': ['iPhone', 'MacBook', 'Windows']
}
def read_regex_patterns(file_path):
    with open(file_path, 'r') as file:
        patterns = {}
        for line in file:
            key, pattern = line.strip().split(':', 1)
            patterns[key.strip()] = pattern.strip()
        return patterns

# Function to read whitelist from file
def read_whitelist(file_path):
    with open(file_path, 'r') as file:
        whitelist = {}
        for line in file:
            key, values = line.strip().split(':', 1)
            whitelist[key.strip()] = [value.strip() for value in values.split(',')]
        return whitelist
# Function to extract entities using regex and whitelist
def extract_entities(text):
    entities = {}

    # Extract entities using regex patterns
    for entity_type, pattern in regex_patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            entities[entity_type] = matches

    # Check against whitelist
    for entity_type, terms in whitelist.items():
        entity_list = []
        for term in terms:
            if term in text:
                entity_list.append(term)
        if entity_list:
            entities[entity_type] = entity_list

    return entities
# Example text
text = "Contact us at example@email.com or 123-456-7890. We are hiring at Google for positions like Apple iPhone developer."

# Extract entities
entities = extract_entities(text)
print(entities)
