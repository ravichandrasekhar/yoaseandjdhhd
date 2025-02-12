import pandas as pd
from pydantic import BaseModel
import csv
import io
class CsvExtractor:
    class InputSchema(BaseModel):
        pass
    def extract_content(self,input: InputSchema,csv_content):
        """Extract and chunk text from a CSV file."""
        text = csv_content.decode("utf-8")
        row_text=''
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            row_text =row_text+ ','.join(row)
        return row_text