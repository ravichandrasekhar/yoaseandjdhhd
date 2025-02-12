import jaydebeapi
from pydantic import BaseModel
import codecs
class JDBC:
    class InputStream(BaseModel):
        InputStream:str
    def __init__(self,config):
        self.jdbc_driver_path =config['jdbc_driver_path']
        self.jdbc_url=config['jdbc_url']
        self.username=config['username']
        self.password=config['password']
        self.driver_class=config['driver_class']
        self.query=config['query']
    def run(self):
        #connection Established for jdbc-mysql
        try:
            conn = jaydebeapi.connect(
                        self.driver_class,
                        self.jdbc_url,
                        [self.username, self.password],
                        self.jdbc_driver_path
                    )
            print("Connected to the MySQL database via JDBC!")

            cursor = conn.cursor()
            query=(self.query)
            query_with_limit = f"{query} LIMIT 100"
            cursor.execute(query_with_limit)

            results = cursor.fetchall()
            for row in results:
                print(row)

            cursor.close()
            conn.close()
            print("Connection closed.")

        except Exception as e:
          print(f"An error occurred: {e}")
