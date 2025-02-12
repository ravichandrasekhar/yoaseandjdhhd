import json
import logging
from typing import Dict, Any

class MainFileGenerator:
    def __init__(self, config: Dict[str, Any], output_path: str = "main.py"):
        self.config = self._clean_config(config)  # Clean the config during initialization
        self.output_path = output_path

    def generate_main_file(self):
        """Generate the `main.py` file dynamically based on the cleaned config."""
        # Step 1: Extract required nodes and imports
        node_imports = self._extract_imports()

        # Step 2: Generate the Python script content
        script_content = self._generate_script_content(node_imports)

        # Step 3: Write the content to `main.py`
        return self._write_to_file(script_content)


    def _clean_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Clean the config to retain only the necessary details."""
        cleaned_nodes = []
        for node in config["nodes"]:
            cleaned_node = {
                "type": node.get("type"),
                "service": node.get("service")
            }
            cleaned_nodes.append(cleaned_node)
        config["nodes"] = cleaned_nodes
        return config

    def _extract_imports(self):
        """Extract required imports from the config."""
        imports = {
            "connectors": "from Factory.connector_factory import ConnectorFactory",
            "text_extraction": "from Factory.text_extract_factory import TextExtractionFactory",
            "chunking": "from Factory.chunking_factory import ChunkingFactory",
            "summarization":"from Factory.summarization_factory  import SummarizationFactory",
            "embeddings": "from Factory.embedding_factory import EmbeddingFactory",
            "search":"from Factory.search_factory import SearchFactory"
            # Add mappings for additional nodes here
        }
        return {node["service"]: imports[node["service"]] for node in self.config["nodes"] if node["service"] in imports}

    def _generate_script_content(self, imports: Dict[str, str]):
        """Generate the script content dynamically."""
        # Dynamic imports
        import_statements = "\n".join(imports.values())

        # Create the node registry dynamically based on the imports, without the full import statement
        node_registry = ",\n        ".join(
            [f'"{service}": {factory_method.split()[-1]}()' for service, factory_method in imports.items()]
        )

        # Convert the config dict to a JSON string
        config_str = json.dumps(self.config, indent=4)

        # Template for main.py
        script_template = f"""
import logging

{import_statements}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Pipeline:
    def __init__(self, config):
        self.config = config
        self.node_registry = {{
            {node_registry}
        }}

    def _create_node(self, node_type):
        if node_type not in self.node_registry:
            raise ValueError(f"Unsupported node type: {{node_type}}")
        return self.node_registry[node_type]

    def process_record(self, record):
        for node_config in self.config["nodes"][1:]:
            node_type = node_config["service"]
            print("calling node : ",node_type)
            node_instance = self._create_node(node_type)
            result = node_instance.process_node(record)
            if "error" in result and result.get("error"):
                logging.error(f"Error processing record at node {{node_type}}: {{result['message']}}")
                break
            record = result.get('record')
        print(record)
        

    def run(self):
        connector = ConnectorFactory()
        out=connector.process_node(self)

if __name__ == "__main__":
    config = {config_str}
    pipeline = Pipeline(config)
    pipeline.run()
"""
        return script_template.strip()

    def _write_to_file(self, content: str):
        """Write the generated content to `main.py`."""
        with open(self.output_path, "w") as f:
            f.write(content)
        print(f"Generated main.py file at {self.output_path}")
        return self.output_path
