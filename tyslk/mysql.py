import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import codecs
# from indexation.indexation import AzureIndexeration

class MySql:
    class InputStream(BaseModel):
        InputStream: str

    def __init__(self, config):
        self.host = config['Host']
        self.port = config['Port']
        self.username = config['UserName']
        self.password = config['password']
        self.database = config['databasename']
        self.query = config['query']
        self.incrementaltime = config['delta_time']
        self.config = config
        # self.indexer = AzureIndexeration(config)
        self.indexer.create_or_update_index()  # Ensuring the index is ready

    def run(self, delta=False):
        try:
            # Establish MySQL connection
            conn = mysql.connector.connect(
                database=self.database,
                user=self.username,
                password=self.password,
                host=self.host,
                port=self.port
            )
            print("Connection established")
            cursor = conn.cursor(dictionary=True)  # Fetch results as dictionaries

            # Adjust query based on delta flag
            if delta:
                now = datetime.now(timezone.utc)
                twelve_hours_ago = now - timedelta(minutes=self.incrementaltime)
                formatted_time = twelve_hours_ago.strftime('%Y-%m-%d %H:%M:%S')

                query = codecs.decode(self.query, 'unicode_escape') + f" WHERE last_modified > '{formatted_time}'"
                print("delta query:", query)
            else:
                query = codecs.decode(self.query, 'unicode_escape')
                print("Full query:", query)

            # Pagination handling
            limit = 100
            skip = 0
            while True:
                query_with_limit = f"{query} LIMIT {limit} OFFSET {skip}"
                cursor.execute(query_with_limit)
                result = cursor.fetchall()

                # Break loop if no records were found
                if not result:
                    break

                # Prepare records for indexing
                records_for_indexing = []
                for record in result:
                    document = {
                        "Id": str(record["Id"]),
                        "Name": record["Name"],
                        "Age": str(record['Age']),
                        "Branch": record['Branch'],
                        "indexation_time": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                    }
                    records_for_indexing.append(document)

                # Perform incremental indexing
                self.indexer.run_incremental_indexing(records_for_indexing)

                if len(result) < limit:
                    break  # If fewer records than the limit, end the loop

                skip += limit  # Increment the offset for the next batch

            conn.commit()  # Commit any pending transactions
            print("Query executed successfully")
            return True  # Indicate success

        except Error as e:
            print(f"Error: {str(e)}")
            return False  # Return failure flag
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                print("MySQL connection closed")