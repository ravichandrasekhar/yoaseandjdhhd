import azure.functions as func
from dotenv import load_dotenv
from FileIndexation.functionHub.blob_trigger_function import blobTriggerFunc
from FileIndexation.functionHub.reset_index_function import resetFunc
from Chatbot.functionHub.chat_responder_function import responderFunc
from FileIndexation.functionHub.csv_connector import csv_connector
# Load environment variables
load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# This is the main Azure Function entry point
app.register_functions(blobTriggerFunc)
app.register_functions(resetFunc)
app.register_functions(responderFunc)
app.register_functions(csv_connector)







