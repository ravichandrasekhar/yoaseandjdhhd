import pandas as pd
import json
# from csv_connector.azureindex import AzureSearchIndexer
import uuid

class CsvConnector:
    def __init__(self, config):
        self.FilePath = config[r'FilePath']
        self.FirstLineIsHeader = config['FirstLineIsHeader']
        # self.indexer = AzureSearchIndexer()
        self.indexer.create_or_update_index()

    def run(self):
        skiprows = 0 if self.FirstLineIsHeader else None
        header = 0 if self.FirstLineIsHeader else None

        if self.FilePath.endswith('.csv'):
            df = pd.read_csv(self.FilePath, skiprows=skiprows, header=header, encoding='windows-1252')
        else:
            df = pd.read_excel(self.FilePath, skiprows=skiprows, header=header)

        # Ensure each document has a unique ID and convert the 'id' to a string
        # df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]  # Add a unique ID to each record
        df['Id'] = df['Id'].astype(str)  # Ensure ID is treated as a string

        # Convert dataframe to list of dictionaries
        records = df.to_dict(orient='records')

        # Upload the documents to the Azure Search index
        self.indexer.upload_documents(records)
