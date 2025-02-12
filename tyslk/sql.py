from sqlalchemy import create_engine, text
from pydantic import BaseModel
import codecs

class Sql:
    class InputStream(BaseModel):
        InputStream: str

    def __init__(self, config):
        self.dburl = config['db_url']
        self.query = config['query']

    def run(self):
        #creating engine for the sqlachemady
        engine = create_engine(self.dburl)
        print(f"Engine created: {engine}")

        # Establish a connection using the engine
        with engine.connect() as conn:
            print("Connection established using SQLAlchemy engine")

            # Decode the query if necessary
            query = codecs.decode(self.query, 'unicode_escape')

            query_with_limit=f"{query} LIMIT 100"
            executable_query = text(query_with_limit)

            # Execute the query
            result = conn.execute(executable_query)

            # Fetch all results
            rows = result.fetchall()

            # List to store fetched records
            all_records = []
            for row in result:
                print(row)

            # Process each row into a dictionary
                # self.indexer.index_documents(document)  # Uncomment if you have indexing logic

            print("Query executed successfully")
            print(rows)
            return all_records
