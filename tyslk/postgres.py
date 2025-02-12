import psycopg2
from psycopg2.extras import RealDictCursor
import codecs
# from .azureindex import AzureSearchIndexer

class postgres:
    def __init__(self, config):
        self.databasename = config['DatabaseName']
        self.host = config['Host']
        self.port = config['Port']
        self.username = config['UserName']
        self.password = config['Password']
        self.query = config['query']
        # self.indexer = AzureSearchIndexer()
        self.indexer.create_or_update_index()

    def run(self):
        conn = psycopg2.connect(database=self.databasename, user=self.username, password=self.password, host=self.host, port=self.port)
        cursor = conn.cursor(cursor_factory=RealDictCursor) 
        skip = 0
        query = codecs.decode(self.query, 'unicode_escape')
        all_records = []  # To collect all the records

        while True:
            cursor.execute(query + ' limit 100 offset ' + str(skip))
            result = cursor.fetchall()
            #all_records.extend(result)  # Add the fetched records to the list
            for i in result:
                i['user_id'] = str( i['user_id'])
            self.indexer.upload_documents(result)
            if cursor.rowcount < 100:
                break
            skip += 100

        conn.commit()
        conn.close()
        
        return all_records
