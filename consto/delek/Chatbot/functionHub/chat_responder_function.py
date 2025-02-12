import azure.functions as func
import os
import uuid
import json
import requests
from swarm import Swarm, Agent
from openai import AzureOpenAI
from Chatbot.functionUtils.ragchatbot import RagBot
from Chatbot.functionUtils.sessions import GetSession
from datetime import datetime
import logging
from azure.data.tables import TableServiceClient
from Chatbot.functionUtils.ragchatbot import RagBot
from dotenv import load_dotenv
import time

load_dotenv()

responderFunc = func.Blueprint() 

AZURE_OPENAI_PREVIEW_API_VERSION = os.getenv("AZURE_OPENAI_PREVIEW_API_VERSION")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

# Azure Table Storage Configuration
TABLE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
TABLE_NAME = os.getenv("TABLE_NAME")
FEEDBACK_TABLE_NAME = os.getenv("FEEDBACK_TABLE_NAME")


if TABLE_STORAGE_CONNECTION_STRING is None:
    raise ValueError("TABLE_STORAGE_CONNECTION_STRING is not set.")
# print(f"TABLE_STORAGE_CONNECTION_STRING: {TABLE_STORAGE_CONNECTION_STRING}")

table_service_client = TableServiceClient.from_connection_string(TABLE_STORAGE_CONNECTION_STRING)
try:
    create_table_client = table_service_client.create_table_if_not_exists(TABLE_NAME)
    get_table_client = table_service_client.get_table_client(TABLE_NAME)
except Exception as e:
    logging.error(f"Failed to create or connect to table: {e}")

try:
    create_feedback_table_client = table_service_client.create_table_if_not_exists(FEEDBACK_TABLE_NAME)
    get_feedback_table_client = table_service_client.get_table_client(FEEDBACK_TABLE_NAME)
except Exception as e:
    logging.error(f"Failed to create or connect to feedback table: {e}")



@responderFunc.route("chatbotResponder")
def chatbotResponder(req: func.HttpRequest):
    try:
        req_body = json.loads(req.get_body())
        question = req_body['question']
        sessionid = req_body['session_id']
        email = req_body['email']
        feedback = req_body.get('feedback')
        feedback_details = req_body.get('feedback_details', {})
        if not isinstance(feedback_details, dict):
            feedback_details = {}
        # Retrieve or create session
        session_obj = GetSession
        session_id = session_obj.get_session_id(sessionid)

        # Get conversation history for the session
        history = session_obj.get_conversation_history(session_id)

        client = AzureOpenAI(
                api_key=AZURE_OPENAI_KEY, 
                azure_deployment=AZURE_OPENAI_MODEL,
                azure_endpoint=AZURE_OPENAI_ENDPOINT, 
                api_version=AZURE_OPENAI_PREVIEW_API_VERSION,
                max_retries=0)

        getUserDetails = f'https://delekus.service-now.com/api/now/table/sys_user?sysparm_query=email={email}&sysparm_fields=sys_id,name&sysparm_limit=1'
        headers = {
                'Content-Type': 'application/json', 
                'Accept': 'application/json',
                'Authorization': 'Basic SVRDT006RDNMM0shc3ZjITUxNzE5MQ=='
            }
      
        response_cases = requests.get(getUserDetails, headers=headers)
       
        res = json.loads(response_cases.text)
        username = res['result'][0]['name'] if len(res['result']) > 0 else "Unknown User"
        sysId = res['result'][0]['sys_id'] if len(res['result']) > 0 else None
    
        entities = get_table_client.query_entities(query_filter=f"session_id eq '{sessionid}'")

        chat_history = []
        session_found = False
        sequence_id = 1  # Initialize sequence ID for questions

        # Check if there are any chat records for the session
        for entity in entities:
            timestamp=entity['timestamp']
            answer_data = json.loads(entity["answer"])
            sisid = entity['session_id']
            
            if sessionid == sisid:
                session_found = True
                sequence_id += 1  # Increment sequence ID for each found question-answer pair in history
                
            chat_history.append({"role": "user", "content": entity["question"], "timestamp": entity["timestamp"]})
            chat_history.append({"role": "bot", "content": answer_data.get("answer"), "timestamp": entity["timestamp"]})
        chat_history = sorted(chat_history, key=lambda x: datetime.fromisoformat(x['timestamp']))
        user_questions = [message["content"] for message in chat_history if message["role"] == "user"]

        if feedback in ["like", "dislike"]:
            store_feedback(session_id, feedback, question, feedback_details, user_questions, username)
        # Determine final question based on session presence
        if not session_found:
            final_question = [{"role":"system", "content":f"sys_id:{sysId}"},{"role": "user", "content": question}]  # Pass the question directly
        else:
            # Get_list_questions = RagBot.get_enriched_question(question, chat_history)
            Lq = RagBot()

            Get_list_questions = Lq.get_enriched_question(question, chat_history)
            final_question = [{"role":"system", "content":f"sys_id:{sysId}"},{"role": "user", "content": Get_list_questions }]

  
        start_time = time.time()

        client = Swarm(client=client)
        get_rag = RagBot()
        agent = Agent(
            name="Delek",
            instructions=f"""You are an AI Agent who drills down documents and answers user questions. 
                You should strictly follow certain rules:
                    1. If the user greets you either in starting of conversation nor in the middle of conversation, respond with {{"answer": "Hello, I am Delek chat assistant. How may I help you?", "citations": null, "answer_found": true}}, otherwise don't greet the user.
                    2. Call get_document_information_agent function to retrieve details about knowledge base articles.    
                    3. Call get_all_open_tickets function to get the list of tickets or open tickets.
                    4. Call get_ticket_details_agent function to get details of specific ticket mentioning it's number.
                    5. If you are not able to find the info with above mentioned functions, Then return you are not able to find the answer.
                    6. When responding with bullet points, add a `\n` at the end of each point to ensure proper display in the UI.
                Strictly follow this JSON response format:
                {{"answer": "string", "citations": "array[string]", "answer_found": "boolean"}}
                """,
            functions=[get_rag.get_document_information, get_rag.get_all_open_tickets, get_rag.get_ticket_details_agent]
        )
        
        # Step 1: Run the agent and retrieve response 
        response = client.run(agent=agent, messages=final_question)
     
        # Step 2: Process response
        answer = json.loads(response.messages[-1]["content"])
        if not answer['answer_found']:
            answer["answer"] = f"I am currently unable to provide an answer to this question '{question}' based on my existing knowledge. However, I recommend reaching out to the help desk by submitting a ticket, or by using support chat or calling 877-DelekIT or 615.224.1178. Wishing you a great day."
        end_time = time.time()

        execution_time = start_time - end_time
        print("execution_time",execution_time)
        history.append({"role": "assistant", "content": answer})

        # Check if answer is valid
        unanswered = "no" if answer.get("answer_found") else "yes"

        # Prepare entity to save in Azure Table Storage with updated schema fields
        timestamp = datetime.utcnow().isoformat()
        entity = {
            "PartitionKey": "Conversation",
            "RowKey": str(uuid.uuid4()),
            "session_id": session_id,
            "sequence_id": sequence_id,
            "sequence_question": json.dumps(user_questions),
            "question": question,
            "username": username,
            "action_taken": "No",
            "unanswered": unanswered,
            "answer": json.dumps(answer),
            "timestamp": timestamp
        }

        # Insert entity into Table Storage
        create_table_client.create_entity(entity)

        answer["RowKey"]=entity['RowKey']
        # Return the response to the user
        logging.info(answer)
        return func.HttpResponse(json.dumps(answer), mimetype="application/json")

    except Exception as e:
        logging.error(e)
        return func.HttpResponse(status_code=500, body="Internal Server Error")
    
def store_feedback(session_id, feedback, question, feedback_details, user_questions, username):
    """
    Store feedback details in the Feedback table in Azure Table Storage.
    """
    feedback_text = feedback_details.get("feedback_text", "")
    other_feedback = feedback_details.get("other_feedback", "")

    feedback_entity = {
        "PartitionKey": "Feedback",
        "RowKey": str(uuid.uuid4()),
        "session_id": session_id,
        "username": username,
        "feedback": feedback,
        "question": question,
        "sequence_question": json.dumps(user_questions),
        "feedback_text": feedback_text,
        "other_feedback": other_feedback,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        # Insert feedback entity into Feedback Table
        create_feedback_table_client.create_entity(feedback_entity)
        logging.info("Feedback stored successfully.")
    except Exception as e:
        logging.error(f"Failed to store feedback: {e}")