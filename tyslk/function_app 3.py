from fastapi import FastAPI, HTTPException, Body
from langchain_mistralai.chat_models import ChatMistralAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
from azure.functions import HttpResponse
import os
from dotenv import load_dotenv
import json
import requests
from requests.auth import HTTPBasicAuth
import functools
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import ChatPromptTemplate
from langchain.chains.llm import LLMChain
import azure.functions as func
from base64 import b64encode
import logging
import time
from langchain_community.chat_models.azure_openai import AzureChatOpenAI

# from fastapi.responses import PlainTextResponse, Response



app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

load_dotenv("./.env")




loginguser = os.getenv("LOGGINGUSER")
password = os.getenv("PASSWORD")


IncidentUser = os.getenv("UserID")  
IncidentPassword = os.getenv("INCIDENTPASSWORD")

print(loginguser,password)
token = b64encode(f'{loginguser}:{password}'.encode('utf-8')).decode('ascii')

# app = FastAPI()

AZURE_OPENAI_ENDPOINT=""
AZURE_OPENAI_EMBEDDING_NAME="text-embedding-ada-002"
AZURE_OPENAI_EMBEDDING_KEY=""

AZURE_OPENAI_PREVIEW_API_VERSION="2023-12-01-preview"
# Azure Cognitive Search endpoint and key
search_endpoint = ""
search_key = ""
index_name = ""
 

client = AzureChatOpenAI(
            api_key = "",
            api_version = AZURE_OPENAI_PREVIEW_API_VERSION,
            azure_endpoint = "",
            model='gpt-35-turbo-16k'
        )

client_azure = AzureOpenAI(
    azure_deployment="text-embedding-ada-002",
    api_version="2023-05-15",
    azure_endpoint="",  # Add your Azure endpoint
    api_key=""          # Add your Azure API key
)


service_endpoint = ""   # Add your Azure Cognitive Search endpoint
api_key = ""

# Initialize Azure Cognitive Search client
credential = AzureKeyCredential(api_key)
search_client = SearchClient(endpoint=service_endpoint, index_name="kb-knowledge1", credential=credential)

import time
import requests
from requests.auth import HTTPBasicAuth
import logging
from fastapi import HTTPException

def get_user_details(sys_id: str, display_value: bool = False):
    '''This function retrieves user details based on the provided sys_id.'''
   
    api_url = f"{sys_id}"
    headers = {
        'Content-Type': 'application/json', 
        'Accept': 'application/json'
    }
    try:    
        response = requests.get(api_url, headers=headers, auth=HTTPBasicAuth(loginguser, password))
        response.raise_for_status()
        data = response.json()
        if data and data['result']:
            return data['result']
        return None
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


def get_open_cases(sys_id: str):
    """This function retrieves details of the open/active cases of the user. It provides the list of cases with its case number and descriptions of the active cases and status of the active cases."""
    user_details = get_user_details(sys_id)
    print(user_details)
    if user_details:
        username = user_details.get('user_name', '') 
        # username = user_details.get('name')
        print("User:----------------",username)
        if username:
            print("username:--------------",username)
            api_url_cases = ""
            params_cases = {
                'sysparm_query': f"opened_for.nameSTARTSWITH{username}^active=True",
            }
            headers_cases = {
                'Content-Type': 'application/json', 
                'Accept': 'application/json'
            }
            try:
                response_cases = requests.get(api_url_cases, params=params_cases, headers=headers_cases, auth=HTTPBasicAuth(loginguser, password))
                print(response_cases.url)
                response_cases.raise_for_status()
                active_cases = response_cases.json()['result']
                print(active_cases)
                # Collecting details of each active case
                case_responses = []
                for case in active_cases:
                    case_response = f"<case>\n\t\t<casenumber>{case.get('number', '')}\n\t\t</casenumber>\n\t\t<casedescription>{case.get('description', '')}\n\t\t</casedescription>\n\t\t<casestatus>{case.get('status', '')}\n\t\t</casestatus>\n</case>"
                    case_responses.append(case_response)
                if len(case_responses) == 0:
                    return "No active cases"
                case_responses = '\n\t'.join(case_responses)
                # print(case_responses)
                return f"<total_active_cases>{len(active_cases)}</total_active_cases>\n<cases>{case_responses}\n</cases>"
                
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=500, detail=f"Error: {e}")
    return None

def chunk_json(json_data, chunk_size):
    """Chunk large JSON data into smaller pieces."""
    for i in range(0, len(json_data), chunk_size):
        yield json_data[i:i + chunk_size]


def knowledge_article(question:str):
    """This function generates responses based on input sys_id by searching Azure Cognitive Search and using MistralAI."""
    # Search for content in Azure Cognitive Search
    embedding = client_azure.embeddings.create(input=question, model="text-embedding-ada-002").data[0].embedding
    vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3, fields="ContentEmbeddings")
    results = search_client.search(search_text=None, vector_queries=[vector_query], select=["id", "content", "sys_id","number","short_description"])

    res = []
    for result in results:
        res.append(f'''{{"Content": "{result['content']}", \n\n"KB_Article": {{\n"sys_id":"{result['sys_id']}" \n"number": "{result['number']}" }}\n\n}}''')
        
    prompts = ",\n".join(res)
    return f"[{prompts}]"

def chat_with_model_endpoint(sys_id):
    try:
        # Call the function to chat with the model
        response = knowledge_article(sys_id)
        print(response)
        return {"responses": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def create_incident(sys_id: str, description:str, short_description:str):
    """Create a new incident in ServiceNow with dynamically generated short_description and description and Caller Id."""
    
    caller_id = get_user_details(sys_id)

    chat_summary = ""

    api_url = ""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = {
        'short_description': short_description,
        'description': description,   
        'caller_id': caller_id, 
        'impact': '1',
        'urgency': '1',
        'contact_type': 'Virtual Agent'
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, auth=HTTPBasicAuth(IncidentUser, IncidentPassword))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error creating incident: {e}")
    


# def get_incident_details(sys_id: str):
#     """Get details of incidents created by the user."""
    # user_details = get_user_details(sys_id)
    # print('User Details :---------------------',user_details)
    # if user_details:
    #     user_sys_id = user_details.get('usr_name', '')
    # api_url = f""
    # headers = {
    #     'Content-Type': 'application/json', 
    #     'Accept': 'application/json'
    # }
    # try:    
    #     response = requests.get(api_url, headers=headers, auth=HTTPBasicAuth(loginguser, password))
    #     response.raise_for_status()
    #     print(response.json())
    #     data = response.json()
    #     if data and data['result']:
    #         data = data['result']
    #     data = None
    
    # except requests.exceptions.RequestException as e:
    #     raise HTTPException(status_code=500, detail=f"Error: {e}")
    # print("data:----------------", json.dumps(data))
    # if data != None:
    #     user_sys_id = data.get('sys_id', '')
    #     print("User:----------------", user_sys_id)
    # user_sys_id = sys_id
    # if user_sys_id:
    #     print("user_sys_id:--------------", user_sys_id)
    #     api_url_incidents = ""
    #     params_incidents = {
    #         'sysparm_query': f"caller_id={user_sys_id}^active=true",
    #         'sysparm_display_value': 'true', 
    #         'sysparm_exclude_reference_link': 'true',
    #         'sysparm_fields': 'number,caller_id,priority,short_description,description,state,sys_id'
    #     }
    #     headers_incidents = {
    #         'Content-Type': 'application/json',
    #         'Accept': 'application/json'
    #     }
    #     try:
    #         response_incidents = requests.get(api_url_incidents, params=params_incidents, headers=headers_incidents, auth=HTTPBasicAuth(loginguser, password))
    #         print(response_incidents.url)
    #         response_incidents.raise_for_status()
    #         incidents = response_incidents.json()['result']
    #         print(incidents)
    #         # Collecting details of each incident
    #         incident_responses = []
    #         for incident in incidents:
    #             incident_response = f"<incident>\n\t\t<incidentnumber>{incident.get('number', '')}\n\t\t</incidentnumber>\n\t\t<incidentstate>{incident.get('state', '')}\n\t\t</incidentstate>\n\t\t<incidentshort_description>{incident.get('short_description', '')}\n\t\t</incidentshort_description>\n\t\t<incident_sys_id>{incident.get('sys_id', '')}\n\t\t</incident_sys_id>\n</incident>"
    #             incident_responses.append(incident_response)
    #         if len(incident_responses) == 0:
    #             return "No incidents found"
    #         incident_responses = '\n\t'.join(incident_responses)
    #         return f"<total_incidents>{len(incidents)}</total_incidents>\n<incidents>{incident_responses}\n</incidents>"
            
    #     except requests.exceptions.RequestException as e:
    #         raise HTTPException(status_code=500, detail=f"Error: {e}")
    # return None



names_to_functions = {
    'get_user_details': functools.partial(get_user_details),
    'get_open_cases': functools.partial(get_open_cases),
    'knowledge_article':functools.partial(knowledge_article),
    'create_incident':functools.partial(create_incident),
    # "get_incident_details": functools.partial(get_incident_details)
}

import re
def extract_function_calls(completion):
    if isinstance(completion, str):
        content = completion
    else:
        content = completion['text']

    pattern = r"<multiplefunctions>(.*?)</multiplefunctions>"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None
    multiplefn = match.group(   )
    print(multiplefn)
    functions = []
    for fn_match in re.finditer(r"<functioncall>(.*?)</functioncall>", multiplefn, re.DOTALL):
        fn_text = fn_match.group(1)
        name = re.search(r"<name>(.*?)</name>", fn_text, re.DOTALL).group(1).replace('"','').replace('\\','').strip()
        arguments = re.search(r"<arguments>(.*?)</arguments>", fn_text, re.DOTALL).group(1)
        args = {}
        for arg in re.finditer(r"<argument>(.*?)</argument>", arguments, re.DOTALL):
            argtxt = arg.group(1)
            argName = re.search(r"<name>(.*?)</name>", argtxt, re.DOTALL).group(1).replace('"','').replace('\\','').strip()
            argValue = re.search(r"<value>(.*?)</value>", argtxt, re.DOTALL).group(1).replace('"','').replace('\\','').strip()
            args[argName] = argValue
        functions.append({"name":name, "args":args})
    return functions

@app.route(route="user_query")
async def user_query(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "POST":
        try:
            start_time = time.time()
            req_body = req.get_json()
            question = req_body.get("question", "")
            sys_id = req_body.get("sys_id", "")
            predefined_questions = {
            "i need a incident": "Create Incident",
            "i am requesting a incident": "Create Incident",
            "can i have incident added": "Create Incident",
            "i am in need of new incident": "Create Incident",
            "i want to create incident": "Create Incident",
            "i want to create an incident": "Create Incident",
            "i need to create incident": "Create Incident",
            "where can i create incident": "Create Incident",
            "how do i get incident created": "Create Incident",
            "how to submit a new incident": "Create Incident",
            "i'd like to submit a incident request": "Create Incident",
            "i need to submit a new incident": "Create Incident",
            "help me submit incident": "Create Incident",
            "submit a incident": "Create Incident",
            "i need to request incident": "Create Incident",
            "i will be submitting an incident": "Create Incident",
            "i have to request incident": "Create Incident",
            "i want to check upon my ticket" : "Check Ticket Status",
            "i need an update on my ticket" : "Check Ticket Status",
            "was the it ticket processed" : "Check Ticket Status",
            "was the inc1234567 resolved" : "Check Ticket Status",
            "was my request reviewed" : "Check Ticket Status",
            "was my outstanding incident closed" : "Check Ticket Status",
            "is my incident ticket progressing" : "Check Ticket Status",
            "i want to check on my requested item" : "Check Ticket Status",
            "i want a follow-upon an open ticket" : "Check Ticket Status",
            "can you provide an update on inc1234567 to me" : "Check Ticket Status",
            "can you find my open it ticket" : "Check Ticket Status",
            "can you check the status of some tickets" : "Check Ticket Status",
            "can i see the pending incident's status" : "Check Ticket Status",
            "can i have an update on a request" : "Check Ticket Status",
            "can i get my ticket's status" : "Check Ticket Status",
            "can i check the status of the open inc1234567" : "Check Ticket Status",
            "i need to check on an open request" : "Check Ticket Status",
            "i want to receive an update on my inc1234567" : "Check Ticket Status",
            "i want a status update on inc1234567" : "Check Ticket Status",
            "can i get the progress on inc1234567" : "Check Ticket Status",
            "how can i check my incident status" : "Check Ticket Status",
            "i need to find the status of inc1234567" : "Check Ticket Status",
            "i want to follow upon inc1234567" : "Check Ticket Status"

    }
    
    # Check if the user's question matches any predefined question
            if question.lower() in predefined_questions:
                response_content = predefined_questions[question.lower()]
                response_data = {
                    "content": response_content,
                }
                return HttpResponse(body=json.dumps(response_data), mimetype="application/json")
            

            # Define your chat prompt template
            template= """  
                    You are a tool which selects function to execute based on the given user query.

                    Functions:
                        Name: knowledge_article, Description: This function generates responses based on input question by searching Azure Cognitive Search and using MistralAI., Params: question

                        Name: get_open_cases, Description: This function retrieves details of the open/active cases of the user. It provides the count and descriptions of the active cases, along with detailed information about each active case.If Description not available Strcitly Ignore, The active cases are classified based on the 'active' parameter in the result., Params: sys_id 

                        Name: get_user_details, Description: This function retrieves user details based on the provided sys_id,  Params: sys_id 

                        Name: create_incident, Description: This function creates a new incident in ServiceNow., Params: sys_id , description(description should be consider by check the summarization of current chat summary and give the detailed chat summary for description), short_description(short_description should be consider by check the summarization of current chat summary and provide one line of the chat Summary.)

                    To use these functions respond with:
                        <multiplefunctions>
                            <functioncall> 
                                <name>"function name"</name> 
                                <arguments>
                                    <argument> 
                                        <name> "argument name" </name>
                                        <value></value> 
                                    </argument>
                                    <argument> 
                                        <name> "argument name" </name>
                                        <value></value> 
                                    </argument>
                                </arguments>
                            <functioncall> 
                                <name>"function name"</name> 
                                <arguments>
                                    <argument> 
                                        <name> "argument name" </name>
                                        <value></value> 
                                    </argument>
                                    <argument> 
                                        <name> "argument name" </name>
                                        <value></value> 
                                    </argument>
                                </arguments>
                            </functioncall>
                            ...
                        </multiplefunctions>

                    Edge cases you must handle:
                    - If there are no functions that match the user request, you will respond politely that you cannot help.
                    Based on the users question select a tool and execute.

                    Question :{question}

                    sys_id:{sys_id} 
            """
            start_time = time.time()
            prompt = ChatPromptTemplate.from_template(template)
            llm = LLMChain(llm=client, prompt=prompt)
            functions = extract_function_calls(llm.invoke({"question": question, "sys_id": sys_id}))
            tool_call = functions[0]
            end_time = time.time()
            logging.error(f"Tool call execution time: {end_time - start_time} seconds")
            result = names_to_functions[tool_call['name']](**tool_call['args'])
            response_text = json.dumps(result)
            logging.error(response_text)
            # Prepare response
            output_format ={

     
        'create_incident': ''' 
                                "1) When providing responses for Creating Incident function, consider these keywords: 'Report an issue', 'facing an issue', 'facing issue', 'Create Incident', 'I want to create an incident', 'is not Working', 'Create an Incident', 'having an issue'. If the user's question contains a related keyword, strictly give the static response 'Create Incident'."
                                "2) If the user's question contains the keyword 'request', strictly give the static response 'Create Request'. For example, if the user asks 'Create Service Request' or 'need to create request', the response should be 'Create Request'."
                                "3) If the user's question contains the keyword 'ticket', strictly give the static response 'Check Ticket Status'. For example, if the user asks 'I want to check upon my ticket' or 'I need an update on my ticket', the response should be 'Check Ticket Status'."
                                "4) If the user's question contains the keyword 'incident', strictly provide the static response 'Create Incident' each and every time without hallucinating."
                            ''',
     
       'knowledge_article': ''' "Strict Response Output Format for Knowledge Article:
                        "answer for the question",
                        "Knowledge Article": Print the link directly (https://mouritechdemo10.service-now.com/kb_view.do?sys_kb_id=<<sys_id should be taken from the Function Response data>>&preview_article=true),
                ''',
                                                 
        'get_open_cases': "If the user is asking for Active/open case details, follow this format: Case Number: <Case Number>, Description: <Description>, Status: <Status>"
        
        
    }

            messages = [SystemMessage(content=f"""
                                            
Consider yourself as a powerful chatbot assistant, who helps employees to get the requested information.

source_function_name : {tool_call['name']}

<rules>

   1) Provide only the direct answer to the question. Do not add any extra information or your own sentences. For example: If the user asks, 'How many active cases do I have?' your response should be, 'You have 10 active cases.'
    2) For questions like "Was the <Any Incident number> resolved?" or "Can you provide an update on <Any Incident number> to me?" or "Can I check the status of the open <Any User Incident number>?" or "I want to receive an update on my <Any User Incident number>" or "I want a status update on <Any User Incident number>" or "Can I get the progress on <Any User Incident number>?" or "I need to find the status of <Any User Incident number>?" or "I want to follow up on <Any User Incident number>", respond strictly with "Check Ticket Status".
    3) Do not start the response with phrases like 'provided Function Response data', 'Based on sys_id', 'Based on the provided information', 'name associated with the given data', 'Based on the provided data', or any similar phrases. Provide the exact response.
    4) Avoid including sys_id details in the final response to the user.
    5) Do not add additional phrases like 'Sure, I can help you with that', 'Based on sys_id', 'Based on the provided information', 'name associated with the given data', 'Based on the provided data', or any similar phrases. Provide the exact response.
    6) Do not include disclaimers.
    7) If the user is asking for case details, follow this format: Case Number: <Case Number>, Description: <Description>, Status: <Status>
    8) Do not add your own content. Use only the given "Function Response data".
    9) If the query concerns beneficiary details, find the 'bene_contact' object within the Function Response data to fetch the answer from the HR profile information.
    10) Strictly add "\n" for new lines generated.
    11) Consider sys_id only from Function Response data. Avoid adding any additional phrases, suggestions, or disclaimers to the Knowledge Article value.
    12) When responding to Creating Incident function, these are the keywords you should consider: 'Report an issue', 'facing an issue', 'facing issue', 'Create Incident', 'I want to create an incident', 'is not Working', 'Create an Incident', 'having an issue'. If the user's question contains related keyword, strictly give the static response as 'Create Incident'.
    13) If the user's question contains the "request" keyword, then only give the static response "Create Request". For example, if the user is asking "Create Service Request" or "need to create request", then the output response should be "Create Request".
    14) If the user is asking a question containing the "ticket" keyword, strictly give the static response as "Check Ticket Status". For example, if the user is asking "I want to check upon my ticket" or "I need an update on my ticket", then the output response should be "Check Ticket Status".
    15) If the user question contains the keyword "incident," strictly provide the static response as "Create Incident" each and every time without hallucinate.

</rules>

{output_format.get(tool_call['name'],'')}

                
sys_id: {sys_id}    
Function Response data: {response_text}
                              
""")]
            messages.append(HumanMessage(content=f"""
Question: {question}
"""))

            # Invoke MistralAI and return response

            result = client.invoke(messages)
            # content = json.dumps(result.dict()['content'])
            # return func.HttpResponse(content[1:-1], status_code=200, mimetype="text/plain")
            end_time = time.time()
            logging.error(f"get_user_query execution time: {end_time - start_time} seconds")
            return func.HttpResponse(result.json(),mimetype="application/json")
        except Exception as e:
            return func.HttpResponse(f"Error: {str(e)}", status_code=500)
    else:
        end_time = time.time()
        logging.error(f"get_user_query execution time: {end_time - start_time} seconds")
        return func.HttpResponse("Method not allowed", status_code=405)