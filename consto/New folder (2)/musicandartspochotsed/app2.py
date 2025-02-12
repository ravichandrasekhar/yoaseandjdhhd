import copy
import json
import os
import logging
import uuid
import logging
import httpx
import requests
from bs4 import BeautifulSoup
import difflib
import asyncio
from quart import (
    Blueprint,
    Quart,
    jsonify,
    make_response,
    request,
    send_from_directory,
    render_template,
    current_app,
)
from quart import Response 
import re
from openai import AsyncAzureOpenAI,AzureOpenAI
from azure.identity.aio import (
    DefaultAzureCredential,
    get_bearer_token_provider
)
import time
from backend.auth.auth_utils import get_authenticated_user_details
from backend.security.ms_defender_utils import get_msdefender_user_json
from backend.history.cosmosdbservice import CosmosConversationClient
from backend.settings import (
    app_settings,
    MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
)
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    convert_to_pf_format,
    format_pf_non_streaming_response,
    parse_multi_columns,
)

bp = Blueprint("routes", __name__, static_folder="static", template_folder="static")

cosmos_db_ready = asyncio.Event()


def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    @app.before_serving
    async def init():
        try:
            app.cosmos_conversation_client = await init_cosmosdb_client()
            cosmos_db_ready.set()
        except Exception as e:
            logging.exception("Failed to initialize CosmosDB client")
            app.cosmos_conversation_client = None
            raise e
    
    return app

@bp.route("/")
async def index():
    return await render_template(
        "index.html",
        title=app_settings.ui.title,
        favicon=app_settings.ui.favicon
    )


@bp.route("/favicon.ico")
async def favicon():
    return await bp.send_static_file("favicon.ico")


@bp.route("/assets/<path:path>")
async def assets(path):
    return await send_from_directory("static/assets", path)


# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
if DEBUG.lower() == "true":
    logging.basicConfig(level=logging.DEBUG)

USER_AGENT = "GitHubSampleWebApp/AsyncAzureOpenAI/1.0.0"
AZURE_OPENAI_STREAM = os.environ.get("AZURE_OPENAI_STREAM", "false")
logger = logging.getLogger('azureLogger')
# DATASOURCE_TYPE = os.environ.get("DATASOURCE_TYPE", "AzureCognitiveSearch")
SHOULD_STREAM = True if AZURE_OPENAI_STREAM.lower() == "true" else False
# Frontend Settings via Environment Variables
#app_settings.base_settings.auth_enabled,
frontend_settings = {
    "auth_enabled": False,#app_settings.base_settings.auth_enabled,
    "feedback_enabled": (
        app_settings.chat_history and
        app_settings.chat_history.enable_feedback
    ),
    "ui": {
        "title": app_settings.ui.title,
        "logo": app_settings.ui.logo,
        "chat_logo": app_settings.ui.chat_logo or app_settings.ui.logo,
        "chat_title": app_settings.ui.chat_title,
        "chat_description": app_settings.ui.chat_description,
        "show_share_button": app_settings.ui.show_share_button,
        "show_chat_history_button": app_settings.ui.show_chat_history_button,
    },
    "sanitize_answer": app_settings.base_settings.sanitize_answer,
    "oyd_enabled": app_settings.base_settings.datasource_type,
}


# Enable Microsoft Defender for Cloud Integration
MS_DEFENDER_ENABLED = os.environ.get("MS_DEFENDER_ENABLED", "true").lower() == "true"


# Initialize Azure OpenAI Client
async def init_openai_client():
    azure_openai_client = None
    
    try:
        # API version check
        if (
            app_settings.azure_openai.preview_api_version
            < MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
        ):
            raise ValueError(
                f"The minimum supported Azure OpenAI preview API version is '{MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION}'"
            )

        # Endpoint
        if (
            not app_settings.azure_openai.endpoint and
            not app_settings.azure_openai.resource
        ):
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_RESOURCE is required"
            )

        endpoint = (
            app_settings.azure_openai.endpoint
            if app_settings.azure_openai.endpoint
            else f"https://{app_settings.azure_openai.resource}.openai.azure.com/"
        )
        # Authentication
        aoai_api_key = app_settings.azure_openai.key
        ad_token_provider = None
        if not aoai_api_key:
            logging.debug("No AZURE_OPENAI_KEY found, using Azure Entra ID auth")
            async with DefaultAzureCredential() as credential:
                ad_token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default"
                )

        # Deployment
        deployment = app_settings.azure_openai.model
        if not deployment:
            raise ValueError("AZURE_OPENAI_MODEL is required")

        # Default Headers
        default_headers = {"x-ms-useragent": USER_AGENT}

        azure_openai_client = AsyncAzureOpenAI(
            api_version=app_settings.azure_openai.preview_api_version,
            api_key=aoai_api_key,
            azure_ad_token_provider=ad_token_provider,
            default_headers=default_headers,
            azure_endpoint=endpoint,
        )
       
        return azure_openai_client
    except Exception as e:
        logging.exception("Exception in Azure OpenAI initialization", e)
        azure_openai_client = None
        raise e



async def init_cosmosdb_client():
    cosmos_conversation_client = None
    if app_settings.chat_history:
        try:
            cosmos_endpoint = (
                f"https://{app_settings.chat_history.account}.documents.azure.com:443/"
            )

            if not app_settings.chat_history.account_key:
                async with DefaultAzureCredential() as cred:
                    credential = cred
                    
            else:
                credential = app_settings.chat_history.account_key

            cosmos_conversation_client = CosmosConversationClient(
                cosmosdb_endpoint=cosmos_endpoint,
                credential=credential,
                database_name=app_settings.chat_history.database,
                container_name=app_settings.chat_history.conversations_container,
                enable_message_feedback=app_settings.chat_history.enable_feedback,
            )
        except Exception as e:
            logging.exception("Exception in CosmosDB initialization", e)
            cosmos_conversation_client = None
            raise e
    else:
        logging.debug("CosmosDB not configured")

    return cosmos_conversation_client


def prepare_model_args(request_body, request_headers):
    request_messages = request_body.get("messages", [])
    messages = []
    if not app_settings.datasource:
        messages = [
            {
                "role": "system",
                "content": app_settings.azure_openai.system_message
            }
        ]

    for message in request_messages:
        if message:
            if message["role"] == "assistant" and "context" in message:
                context_obj = json.loads(message["context"])
                messages.append(
                    {
                        "role": message["role"],
                        "content": message["content"],
                        "context": context_obj
                    }
                )
            else:
                messages.append(
                    {
                        "role": message["role"],
                        "content": message["content"]
                    }
                )

    user_json = None
    if (MS_DEFENDER_ENABLED):
        authenticated_user_details = get_authenticated_user_details(request_headers)
        conversation_id = request_body.get("conversation_id", None)
        application_name = app_settings.ui.title
        user_json = get_msdefender_user_json(authenticated_user_details, request_headers, conversation_id, application_name)

    model_args = {
        "messages": messages,
        "temperature": app_settings.azure_openai.temperature,
        "max_tokens": app_settings.azure_openai.max_tokens,
        "top_p": app_settings.azure_openai.top_p,
        "stop": app_settings.azure_openai.stop_sequence,
        "stream": app_settings.azure_openai.stream,
        "model": app_settings.azure_openai.model,
        "user": user_json
    }

    if app_settings.datasource:
        model_args["extra_body"] = {
            "data_sources": [
                app_settings.datasource.construct_payload_configuration(
                    request=request
                )
            ]
        }

    model_args_clean = copy.deepcopy(model_args)
    if model_args_clean.get("extra_body"):
        secret_params = [
            "key",
            "connection_string",
            "embedding_key",
            "encoded_api_key",
            "api_key",
        ]
        for secret_param in secret_params:
            if model_args_clean["extra_body"]["data_sources"][0]["parameters"].get(
                secret_param
            ):
                model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                    secret_param
                ] = "*****"
        authentication = model_args_clean["extra_body"]["data_sources"][0][
            "parameters"
        ].get("authentication", {})
        for field in authentication:
            if field in secret_params:
                model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                    "authentication"
                ][field] = "*****"
        embeddingDependency = model_args_clean["extra_body"]["data_sources"][0][
            "parameters"
        ].get("embedding_dependency", {})
        if "authentication" in embeddingDependency:
            for field in embeddingDependency["authentication"]:
                if field in secret_params:
                    model_args_clean["extra_body"]["data_sources"][0]["parameters"][
                        "embedding_dependency"
                    ]["authentication"][field] = "*****"

    logging.debug(f"REQUEST BODY: {json.dumps(model_args_clean, indent=4)}")

    return model_args

def remove_html_tags(html):
    # Replace HTML tags with a newline
    clean_text = re.sub(r'<[^>]+>', '\n', html)
    # Replace non-breaking spaces with regular spaces and strip leading/trailing whitespace
    clean_text = clean_text.replace('\xa0', ' ').strip()
    # Optionally, remove consecutive newlines
    clean_text = re.sub(r'\n+', '\n', clean_text)
    return clean_text
async def promptflow_request(request):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_settings.promptflow.api_key}",
        }
        # Adding timeout for scenarios where response takes longer to come back
        logging.debug(f"Setting timeout to {app_settings.promptflow.response_timeout}")
        async with httpx.AsyncClient(
            timeout=float(app_settings.promptflow.response_timeout)
        ) as client:
            pf_formatted_obj = convert_to_pf_format(
                request,
                app_settings.promptflow.request_field_name,
                app_settings.promptflow.response_field_name
            )
            # NOTE: This only support question and chat_history parameters
            # If you need to add more parameters, you need to modify the request body
            response = await client.post(
                app_settings.promptflow.endpoint,
                json={
                    app_settings.promptflow.request_field_name: pf_formatted_obj[-1]["inputs"][app_settings.promptflow.request_field_name],
                    "chat_history": pf_formatted_obj[:-1],
                },
                headers=headers,
            )
        resp = response.json()
        resp["id"] = request["messages"][-1]["id"]
        return resp
    except Exception as e:
        logging.error(f"An error occurred while making promptflow_request: {e}")

def is_valid_json(content):
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        logger.debug("Invalid JSON")
        return False
def get_openai_response(messages,model_name,json_mode=False):
        response=[]
        if model_name==app_settings.azure_openai.model:
            client = AzureOpenAI(
                    api_key=app_settings.azure_openai.key,
                    api_version=app_settings.azure_openai.preview_api_version,
                    azure_endpoint=app_settings.azure_openai.endpoint
                )
        else:
            client = AzureOpenAI(
                    api_key=app_settings.azure_openai.key,
                    api_version=app_settings.azure_openai.preview_api_version,
                    azure_endpoint=app_settings.azure_openai.endpoint
                )
        try:
            if json_mode:
                
                response = client.chat.completions.create(
                    model=model_name,
                    response_format={ "type": "json_object" },
                    messages=messages,
                    temperature=float( app_settings.azure_openai.temperature),
                    top_p=float(app_settings.azure_openai.top_p),
                    max_tokens=int(app_settings.azure_openai.max_tokens),
                    stream=SHOULD_STREAM,
                    stop=parse_multi_columns(app_settings.azure_openai.stop_sequence) if app_settings.azure_openai.stop_sequence else None
                )
            else:
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=float(app_settings.azure_openai.temperature),
                    top_p=float(app_settings.azure_openai.top_p),
                    max_tokens=int(app_settings.azure_openai.max_tokens),
                    stream=SHOULD_STREAM,
                    stop=parse_multi_columns(app_settings.azure_openai.stop_sequence) if app_settings.azure_openai.stop_sequence else None
                )
         
        except Exception as e:
            logger.debug(e)
            
        return response
    
def generate_answer_with_citations(query, documents, response):
    
    
    def get_documents_used_as_citations(text, documents):
        # Extract document numbers from the text
        doc_numbers = re.findall(r'\[doc(\d+)\]', text)
        # Convert to zero-based indices and remove duplicates
        doc_indices = list(set(int(num) - 1 for num in doc_numbers))
        # Filter documents and store them in a dictionary with their original indices as keys
        filtered_documents = {i: documents[i] for i in doc_indices if 0 <= i < len(documents)}
        return filtered_documents
    
    
    def create_prompt(query, documents):
        prompt = f"""
        \n\n QUESTION: '{query}' \n\n DOCUMENTS:\n"""
        for idx, doc in enumerate(documents, 1):
            prompt += f"'Document {idx}: {doc['cleanedContent']} [doc{idx}]'\n"

        prompt+="""
        INSTRUCTIONS: Mention the SKU number and product name is possible.Answer it in a nice detailed way and ensure your explanation is thorough, if user has mentioned in question a particular response format(example: Tabular, Bulleted) follow that when crafting you response answer include citations in the format [doc1], [doc2], etc. avoid single line replies. Never mention 'Based on the given documents' or 'as mentioned in Document 1' or any related phrase; the user should not know that documents were provided. 
            For comparison related user questions analyze the documents and do detailed comparison feature wise, When crafting your response, include citations from relevant documents using the [docX] format, where X refers to the citation.
        """
        return prompt
    
    def create_email_prompt(query, documents):
        prompt = f"""
        \n\n you are a customer service agent of Stanley Black and Decker. This is the body of an email sent to you by the customer : '{query}' \n\n DOCUMENTS:\n"""
        for idx, doc in enumerate(documents, 1): 
            prompt += f"'Document {idx}: {doc['cleanedContent']} [doc{idx}]'\n"

            prompt+= f""" Follow the template below.
  **Subject:** Regarding your inquiry (summarize this {query} here)

  Dear Customer,

  Thank you for contacting Stanley Black & Decker customer service. We appreciate you reaching out about ( summarize this {query} here).

  I understand you're interested in [Summarize key points from the customer's query based on the documents and avoiding single line summaries].

  [Analyze the documents (cleanedContent) to craft a personalized response that addresses the customer's specific inquiry. Use the information from the documents to answer their questions, solve their problems, or provide relevant details about Stanley Black & Decker products.]

  For your reference, you can find more details about our products on our website: [link to Stanley Black & Decker website]

  We hope this information helps. Please don't hesitate to contact us if you have any further questions.

  Sincerely,

  The music and arts  Service Team
  
  
  you response should be json structure : {{"answer" : "<generated email>"}}
  """
        return prompt

    
    def create_category_prompt(query):
        prompt=f"""


                You are an intelligent assistant trained to classify user queries into specific categories based on the understanding of the context and type of the user query. Here are the categories you need to classify the questions into, along with the description and examples to help you understand each category:

                Compatibility: Classify question into this category when the context of the question is about comparing a product with other products or versions.

                    Example: "Is the DEWALT ToughSystem® 2.0 Two-Drawer Unit DWST08320 designed to be compatible with the ToughSystem 1.0 versions without the need for an adapter or insert?"
                    Troubleshooting: Questions related to fixing issues or problems with a product.

                Troubleshooting:  Classify question into this category when the context of the question is related to fixing issues or problems with a product. These typically involve identifying and resolving malfunctions or errors.
                    Example: "The DCN930B is jammed. What are the steps to unjam it?"

                Parts and Accessories: Classify question into this category when questions is about specific parts or accessories for a product. 
                    Example: "Customer needs to know the correct replacement spool for the DCST920B."

                Tool Use and Applications: Classify question into this category when questions is about how to use a tool or the recommended applications for a tool. These questions often seek advice on effective usage or specific tasks the tool is suited for.
                    Example: "What is the recommended application for the DEWALT DCD996B 20V MAX XR Hammer Drill (model number DCD996B) in masonry work, and how can it be used effectively for drilling into concrete or brick surfaces?"
                
                Features and Specifications: Classify question into this category when questions is about the features or specifications of a product. These are typically inquiries about the technical details or capabilities of a product.
                    Example: "What is the accuracy of the 5-Spot Red Laser Level DW085K?"
                
                Processes: Classify question into this category when questions is about processes, such as warranty, returns, or policies. These often involve understanding procedural steps or company policies.
                    Example: "How can I reprocess the request for the 90-days money back guarantee policy?"
                
                Licensed Partner: Classify question into this category when questions is about licensed partners or related information. These inquiries seek information about authorized partners or dealers.
                    Example: "What is the licensed partner information for the DXPW3425 pressure washer?"

                Your task is to analyze the question asked by the user and classify it into one of the above categories. 
                Your response should be JSON structure: {{"category" : <category identified>}}

            """
        return prompt
    
    def extract_unique_doc_references(text):
        matches = re.findall(r'doc\d+', text)
        unique_matches = list(set(matches))
        return unique_matches

    def get_system_message():
        return {
            "role": "system",
            "content": ("INSTRUCTIONS: You are an AI assistant providing answers about tool product information. "
                        "When crafting your response, include citations from relevant documents using the [docX] format, where X refers to the citation. "
                        "Use ONLY those documents that directly relate to the user's question; if no relevant information is found in the documents given, answer that you are unable to find the given information. Strictly Your answer should not include any information which is not present in the document")
        }
        #  "Format: Organize the response with clear headings, bullet points, and numbered lists to improve readability and structure. "
    def get_highlight_system_message():
        return {
            "role": "system",
            "content": ("INSTRUCTIONS: As an AI assistant, your responsibility is to identify lines from citations that are relevant to answering specific questions. When provided with a question, along with the documents containing citations used to formulate the answer, and specific citation numbers indicating their contributions to generating the answer, your task is to extract the original, unmodified lines from those specific citations used in formulating the answer. if no relevant information is found in the documents given with respect to the user question, answer that you are unable to find the given information. Strictly Your answer should not include any information which is not present in the documents")
        }
    

    def get_highlight_info_prompt(question,generated_answer,documents_used,doc_references): 
        doc_references=', '.join(doc_references)
        # Constructing the prompt
        prompt = f"""
        You're provided with a scenario where an LLM (Large Language Model) was given a question and provided an answer using only the documents given below. Your task is to identify the original, unmodified line from each document that the LLM used to generate the answer.

        Here's the scenario:
        An LLM was asked the question: "{question}"
        The answer it responded with was: "{generated_answer}"

        You're given a set of documents. Each document has a number and contains relevant information that the LLM could have used to generate the answer.
        Documents:
        """

        for key,docValue in documents_used.items():
            prompt += f"[Document {key}]\n{docValue['cleanedContent']}\n\n"
        
            
        prompt+=f""". /n
        Your task is to structure your response in JSON format. Each document has a key representing its number like Document Numner(0,1,4,..etc), and the value should be the exact line from that document that the LLM used.

        For example, if the  documents 0 and 2 are passed to you your response should look like this: {{"Document 0": "<line used from document 0 to generate the questions answer>", "Document 2": "<line used from document 2 to generate the questions answer>"}}.

       
        STRICTLY extract and provide exact unmodified relevant line from each of the documents provided above. while returning the lines ensure to keep any newline charachet by \\n or <br/> intact in lines if present in given document.\\n or <br/> should not be replace at any cost, it should be present in the response.  If you are not able to find specific relevant lines from a specific document to generate the answer, simply provide an empty JSON object for that document, do not generate a line from your own for response.

        Ensure your JSON response is valid, without any additional text or formatting.
    
        """   
        return {
        "role": "user",
        "content": (prompt)
    }    
    def get_openai_response(messages,model_name,json_mode=False):
        response=[]
        if model_name==app_settings.azure_openai.model:
            client = AzureOpenAI(
                    api_key=app_settings.azure_openai.key,
                    api_version=app_settings.azure_openai.preview_api_version,
                    azure_endpoint=app_settings.azure_openai.endpoint
                )
        else:
            client = AzureOpenAI(
                    api_key=app_settings.azure_openai.key,
                    api_version=app_settings.azure_openai.preview_api_version,
                    azure_endpoint=app_settings.azure_openai.endpoint
                )
        try:
            if json_mode:
              response = client.chat.completions.create(
                    model=model_name,
                    response_format={ "type": "json_object" },
                    messages=messages,
                    temperature=float( app_settings.azure_openai.temperature),
                    top_p=float(app_settings.azure_openai.top_p),
                    max_tokens=int(app_settings.azure_openai.max_tokens),
                    stream=SHOULD_STREAM,
                    stop=parse_multi_columns(app_settings.azure_openai.stop_sequence) if app_settings.azure_openai.stop_sequence else None
                )
            else:
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=float(app_settings.azure_openai.temperature),
                    top_p=float(app_settings.azure_openai.top_p),
                    max_tokens=int(app_settings.azure_openai.max_tokens),
                    stream=SHOULD_STREAM,
                    stop=parse_multi_columns(app_settings.azure_openai.stop_sequence) if app_settings.azure_openai.stop_sequence else None
                )

        except Exception as e:
            logger.debug(e)
        return response
       
    
    citation_references=extract_unique_doc_references(response.choices[0].message.content)
    documents_used = get_documents_used_as_citations(response.choices[0].message.content,documents)
                    
    try:
                if documents_used:
                    valid_highlights_response = False
                    highlight_messages=[get_highlight_system_message(),get_highlight_info_prompt(query,response.choices[0].message.content,documents_used,citation_references)]
                    response_highlight = get_openai_response(highlight_messages,app_settings.azure_openai.model,json_mode=True)
                    try:
                        llmJsonResponse = json.loads(response_highlight.choices[0].message.content)
                        valid_highlights_response = True
                    except json.JSONDecodeError as e:
                        logger.debug(f"Error decoding JSON response: {e}")
                    if valid_highlights_response:
                        #documents_dict= {obj["id"].split(" ")[1]: obj for obj in documents}
                        for key in llmJsonResponse:
                            try:
                                if key.startswith("Document") or key.startswith("document"):
                                    document_number = int(key.split(" ")[1])
                                elif key.startswith("doc") or key.startswith("Doc"):
                                    document_number = int(key[-1])
                                else:
                                    continue  # Skip keys that don't match the expected format
                                documents[document_number]["content"] = highlight_text_func(documents[document_number]["content"], llmJsonResponse[key],set())
                                
                            except (IndexError, ValueError) as e:
                                logger.debug(f"Error processing document key '{key}': {e}")
                        #documents=list(documents_dict.values())
                        
    except Exception as e:
                logger.debug(f"Error in processing documents: {e}")
            
    response.choices[0].message.context = {"citations": documents}
    
    return response

def send_audit_entry(user_id, app_name, status, model_name,table_name,step_name, input_tokens, output_tokens, total_tokens, user_question, bot_answer, response_time):
    url = "https://func-mt-openai-audit.azurewebsites.net/api/add_audit_entry"

    body = {
        "user_id": str(user_id),
        "app_name": app_name,
        "status": status,
        "model_name": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "response_time": response_time,
        "table_name": table_name,
        "step_name": step_name,
        "user_question": user_question,
        "bot_answer": bot_answer
    }

    payload = json.dumps(body)
  
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    print("response in audit send",response.text)
    return response.text
       
async def send_chat_request(request_body, request_headers):
    filtered_messages = []
    messages = request_body.get("messages", [])
    
    # Filter out messages with role 'tool'
    for message in messages:
        if message.get("role") != 'tool':
            filtered_messages.append(message)
    
    # Update the messages in the request body
    request_body['messages'] = filtered_messages
    
    
    # Prepare model arguments
    model_args = prepare_model_args(request_body, request_headers)
    
    # Initialize variables
    audit_status = "successful"
    app_name = "music and arts"
    model_name = model_args.get("model")
    user_question = messages[-1].get("content") if messages else ""
    print("user_question", user_question)
    response = None  # Initialize response to handle exceptions
    apim_request_id = None
    start_time = time.time()

    try:
        # Initialize the OpenAI client
        azure_openai_client = await init_openai_client()
        
        # Make the chat completion request
        raw_response = await azure_openai_client.chat.completions.with_raw_response.create(**model_args)
        
        if isinstance(raw_response, AsyncAzureOpenAI):
            response_data = []
            async for chunk in raw_response:
                response_data.append(chunk)  # Collect the chunks of the response
            response = ''.join(response_data)
          
        else:
            response = raw_response.parse()
        
        
        apim_request_id = raw_response.headers.get("apim-request-id")
        
        # Process citations if present
        if hasattr(response.choices[0].message, 'context'):
            citations = response.choices[0].message.context.get("citations", [])
            for citation in citations:
                 
                citation["cleanedContent"] = citation["content"].replace("<br/>", " \\n ").replace("\n", " \\n ")
                citation["content"] = citation["content"].replace("\\n", "")
            response = generate_answer_with_citations(messages[-1]["content"], citations, response)
    
    except Exception as e:
        logging.exception("Exception in send_chat_request")
        audit_status = "failed"
        response = {
            "messages": [{"content": str(e)}]  # Set a default error response
        }
    
    finally:
        # Calculate response details for audit
        user_id= uuid.uuid4()
        
        end_time = time.time()
        
        response_time = end_time - start_time
     
        bot_answer = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else ""
      
       
        input_tokens = len(user_question.split()) if user_question else 0
        output_tokens = len(bot_answer.split()) if bot_answer else 0
        total_tokens = input_tokens + output_tokens
        
        # Log the audit entry
        send_audit_entry(
    user_id=user_id,
    app_name=app_name,
    status=audit_status,
    model_name=model_name,
    table_name="musicandartspoc",
    step_name="QueryProcessing",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    total_tokens=total_tokens,
    response_time=response_time,
    user_question=user_question,
    bot_answer=bot_answer
)

        print("Audit logged successfully.",send_audit_entry)
    
    return response, apim_request_id

async def stream_chat_request(request_body, request_headers):
    response, apim_request_id = await send_chat_request(request_body, request_headers)
    history_metadata = request_body.get("history_metadata", {})
    
    async def generate():
        async for completionChunk in response:
            yield format_stream_response(completionChunk, history_metadata, apim_request_id)

    return generate()


async def complete_chat_request(request_body, request_headers):
    if app_settings.base_settings.use_promptflow:
        response = await promptflow_request(request_body)
        history_metadata = request_body.get("history_metadata", {})
        return format_pf_non_streaming_response(
            response,
            history_metadata,
            app_settings.promptflow.response_field_name,
            app_settings.promptflow.citations_field_name
        )
    else:
        response, apim_request_id = await send_chat_request(request_body, request_headers)
        history_metadata = request_body.get("history_metadata", {})
        
        return format_non_streaming_response(response, history_metadata, apim_request_id)

async def conversation_internal(request_body,request_headers):
    try:
        if app_settings.azure_openai.stream and not app_settings.base_settings.use_promptflow:
            result = await stream_chat_request(request_body, request_headers)
            response = await make_response(format_as_ndjson(result))
            response.timeout = None
            response.mimetype = "application/json-lines"
            return response
        else:
            result = await complete_chat_request(request_body, request_headers)
            return jsonify(result)

    except Exception as ex:
        logging.exception(ex)
        if hasattr(ex, "status_code"):
            return jsonify({"error": str(ex)}), ex.status_code
        else:
            return jsonify({"error": str(ex)}), 500

def highlight_text_func(html_content, text_to_highlight,highlighted_text):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all text nodes in the soup
    text_nodes = soup.find_all(text=True)
    text_node_strings = [str(text_node) for text_node in text_nodes]

    # Normalize all text nodes
    normalized_text_nodes = [''.join(e for e in text_node if e.isalnum()).lower() for text_node in text_node_strings]
    # Find the closest match
    lines_to_match =text_to_highlight.split('\n') if '\n' in text_to_highlight else text_to_highlight.split('<br/>')
    for line in lines_to_match:
        if line:
            normalized_text_to_highlight = ''.join(e for e in line if e.isalnum()).lower()
            closest_matches = difflib.get_close_matches(normalized_text_to_highlight, normalized_text_nodes, n=1, cutoff=0.7)
            if closest_matches:
                closest_match = closest_matches[0]
                for text_node in text_nodes:
                    normalized_text_node = ''.join(e for e in text_node if e.isalnum()).lower()
                    if normalized_text_node == closest_match:
                        highlighted_text.add(closest_match)
                        span = soup.new_tag('span', style='background-color: yellow;')
                        span.string = text_node
                        text_node.replace_with(span)

    return str(soup)
@bp.route("/conversation", methods=["POST"])
async def conversation():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()

    return await conversation_internal(request_json, request.headers)
@bp.route("/frontend_settings", methods=["GET"])
def get_frontend_settings():
    try:
        return jsonify(frontend_settings), 200
    except Exception as e:
        logging.exception("Exception in /frontend_settings")
        return jsonify({"error": str(e)}), 500


## Conversation History API ##
@bp.route("/history/generate", methods=["POST"])
async def add_conversation():
    await cosmos_db_ready.wait()
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    try:
        # make sure cosmos is configured
        if not current_app.cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        # check for the conversation_id, if the conversation is not set, we will create a new one
        history_metadata = {}
        if not conversation_id:
            title = await generate_title(request_json["messages"])
            conversation_dict = await current_app.cosmos_conversation_client.create_conversation(
                user_id=user_id, title=title
            )
            conversation_id = conversation_dict["id"]
            history_metadata["title"] = title
            history_metadata["date"] = conversation_dict["createdAt"]

        messages = request_json["messages"]
        if len(messages) > 0 and messages[-1]["role"] == "user":
            createdMessageValue = await current_app.cosmos_conversation_client.create_message(
                uuid=str(uuid.uuid4()),
                conversation_id=conversation_id,
                user_id=user_id,
                input_message=messages[-1],
            )
            if createdMessageValue == "Conversation not found":
                raise Exception(
                    "Conversation not found for the given conversation ID: "
                    + conversation_id
                    + "."
                )
        else:
            raise Exception("No user message found")

        # Submit request to Chat Completions for response
        request_body = await request.get_json()
        history_metadata["conversation_id"] = conversation_id
        request_body["history_metadata"] = history_metadata
        return await conversation_internal(request_body, request.headers)

    except Exception as e:
        logging.exception("Exception in /history/generate")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/update", methods=["POST"])
async def update_conversation():
    await cosmos_db_ready.wait()
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    try:
        # make sure cosmos is configured
        if not current_app.cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        # check for the conversation_id, if the conversation is not set, we will create a new one
        if not conversation_id:
            raise Exception("No conversation_id found")

        ## Format the incoming message object in the "chat/completions" messages format
        ## then write it to the conversation history in cosmos
        messages = request_json["messages"]
        if len(messages) > 0 and messages[-1]["role"] == "assistant":
            if len(messages) > 1 and messages[-2].get("role", None) == "tool":
                # write the tool message first
                await current_app.cosmos_conversation_client.create_message(
                    uuid=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    user_id=user_id,
                    input_message=messages[-2],
                )
            # write the assistant message
            await current_app.cosmos_conversation_client.create_message(
                uuid=messages[-1]["id"],
                conversation_id=conversation_id,
                user_id=user_id,
                input_message=messages[-1],
            )
        else:
            raise Exception("No bot messages found")

        # Submit request to Chat Completions for response
        response = {"success": True}
        return jsonify(response), 200

    except Exception as e:
        logging.exception("Exception in /history/update")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/message_feedback", methods=["POST"])
async def update_message():
    await cosmos_db_ready.wait()
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for message_id
    request_json = await request.get_json()
    message_id = request_json.get("message_id", None)
    message_feedback = request_json.get("message_feedback", None)
    try:
        if not message_id:
            return jsonify({"error": "message_id is required"}), 400

        if not message_feedback:
            return jsonify({"error": "message_feedback is required"}), 400

        ## update the message in cosmos
        updated_message = await current_app.cosmos_conversation_client.update_message_feedback(
            user_id, message_id, message_feedback
        )
        if updated_message:
            return (
                jsonify(
                    {
                        "message": f"Successfully updated message with feedback {message_feedback}",
                        "message_id": message_id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "error": f"Unable to update message {message_id}. It either does not exist or the user does not have access to it."
                    }
                ),
                404,
            )

    except Exception as e:
        logging.exception("Exception in /history/message_feedback")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/delete", methods=["DELETE"])
async def delete_conversation():
    await cosmos_db_ready.wait()
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    try:
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400

        ## make sure cosmos is configured
        if not current_app.cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        ## delete the conversation messages from cosmos first
        deleted_messages = await current_app.cosmos_conversation_client.delete_messages(
            conversation_id, user_id
        )

        ## Now delete the conversation
        deleted_conversation = await current_app.cosmos_conversation_client.delete_conversation(
            user_id, conversation_id
        )

        return (
            jsonify(
                {
                    "message": "Successfully deleted conversation and messages",
                    "conversation_id": conversation_id,
                }
            ),
            200,
        )
    except Exception as e:
        logging.exception("Exception in /history/delete")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/list", methods=["GET"])
async def list_conversations():
    await cosmos_db_ready.wait()
    offset = request.args.get("offset", 0)
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## make sure cosmos is configured
    if not current_app.cosmos_conversation_client:
        raise Exception("CosmosDB is not configured or not working")

    ## get the conversations from cosmos
    conversations = await current_app.cosmos_conversation_client.get_conversations(
        user_id, offset=offset, limit=25
    )
    if not isinstance(conversations, list):
        return jsonify({"error": f"No conversations for {user_id} were found"}), 404

    ## return the conversation ids

    return jsonify(conversations), 200


@bp.route("/history/read", methods=["POST"])
async def get_conversation():
    await cosmos_db_ready.wait()
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    ## make sure cosmos is configured
    if not current_app.cosmos_conversation_client:
        raise Exception("CosmosDB is not configured or not working")

    ## get the conversation object and the related messages from cosmos
    conversation = await current_app.cosmos_conversation_client.get_conversation(
        user_id, conversation_id
    )
    ## return the conversation id and the messages in the bot frontend format
    if not conversation:
        return (
            jsonify(
                {
                    "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
                }
            ),
            404,
        )

    # get the messages for the conversation from cosmos
    conversation_messages = await current_app.cosmos_conversation_client.get_messages(
        user_id, conversation_id
    )

    ## format the messages in the bot frontend format
    messages = [
        {
            "id": msg["id"],
            "role": msg["role"],
            "content": msg["content"],
            "createdAt": msg["createdAt"],
            "feedback": msg.get("feedback"),
        }
        for msg in conversation_messages
    ]

    return jsonify({"conversation_id": conversation_id, "messages": messages}), 200


@bp.route("/history/rename", methods=["POST"])
async def rename_conversation():
    await cosmos_db_ready.wait()
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    if not conversation_id:
        return jsonify({"error": "conversation_id is required"}), 400

    ## make sure cosmos is configured
    if not current_app.cosmos_conversation_client:
        raise Exception("CosmosDB is not configured or not working")

    ## get the conversation from cosmos
    conversation = await current_app.cosmos_conversation_client.get_conversation(
        user_id, conversation_id
    )
    if not conversation:
        return (
            jsonify(
                {
                    "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
                }
            ),
            404,
        )

    ## update the title
    title = request_json.get("title", None)
    if not title:
        return jsonify({"error": "title is required"}), 400
    conversation["title"] = title
    updated_conversation = await current_app.cosmos_conversation_client.upsert_conversation(
        conversation
    )

    return jsonify(updated_conversation), 200


@bp.route("/history/delete_all", methods=["DELETE"])
async def delete_all_conversations():
    await cosmos_db_ready.wait()
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    # get conversations for user
    try:
        ## make sure cosmos is configured
        if not current_app.cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        conversations = await current_app.cosmos_conversation_client.get_conversations(
            user_id, offset=0, limit=None
        )
        if not conversations:
            return jsonify({"error": f"No conversations for {user_id} were found"}), 404

        # delete each conversation
        for conversation in conversations:
            ## delete the conversation messages from cosmos first
            deleted_messages = await current_app.cosmos_conversation_client.delete_messages(
                conversation["id"], user_id
            )

            ## Now delete the conversation
            deleted_conversation = await current_app.cosmos_conversation_client.delete_conversation(
                user_id, conversation["id"]
            )
        return (
            jsonify(
                {
                    "message": f"Successfully deleted conversation and messages for user {user_id}"
                }
            ),
            200,
        )

    except Exception as e:
        logging.exception("Exception in /history/delete_all")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/clear", methods=["POST"])
async def clear_messages():
    await cosmos_db_ready.wait()
    ## get the user id from the request headers
    authenticated_user = get_authenticated_user_details(request_headers=request.headers)
    user_id = authenticated_user["user_principal_id"]

    ## check request for conversation_id
    request_json = await request.get_json()
    conversation_id = request_json.get("conversation_id", None)

    try:
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400

        ## make sure cosmos is configured
        if not current_app.cosmos_conversation_client:
            raise Exception("CosmosDB is not configured or not working")

        ## delete the conversation messages from cosmos
        deleted_messages = await current_app.cosmos_conversation_client.delete_messages(
            conversation_id, user_id
        )

        return (
            jsonify(
                {
                    "message": "Successfully deleted messages in conversation",
                    "conversation_id": conversation_id,
                }
            ),
            200,
        )
    except Exception as e:
        logging.exception("Exception in /history/clear_messages")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/ensure", methods=["GET"])
async def ensure_cosmos():
    await cosmos_db_ready.wait()
    if not app_settings.chat_history:
        return jsonify({"error": "CosmosDB is not configured"}), 404

    try:
        success, err = await current_app.cosmos_conversation_client.ensure()
        if not current_app.cosmos_conversation_client or not success:
            if err:
                return jsonify({"error": err}), 422
            return jsonify({"error": "CosmosDB is not configured or not working"}), 500

        return jsonify({"message": "CosmosDB is configured and working"}), 200
    except Exception as e:
        logging.exception("Exception in /history/ensure")
        cosmos_exception = str(e)
        if "Invalid credentials" in cosmos_exception:
            return jsonify({"error": cosmos_exception}), 401
        elif "Invalid CosmosDB database name" in cosmos_exception:
            return (
                jsonify(
                    {
                        "error": f"{cosmos_exception} {app_settings.chat_history.database} for account {app_settings.chat_history.account}"
                    }
                ),
                422,
            )
        elif "Invalid CosmosDB container name" in cosmos_exception:
            return (
                jsonify(
                    {
                        "error": f"{cosmos_exception}: {app_settings.chat_history.conversations_container}"
                    }
                ),
                422,
            )
        else:
            return jsonify({"error": "CosmosDB is not working"}), 500
async def generate_content(conversation_messages) -> str:
    ## make sure the messages are sorted by _ts descending
    content_prompt = "Summarize the conversation so far into a 4-word or less title. Do not use any quotation marks or punctuation. Do not include any other commentary or description."

    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in conversation_messages
    ]
    messages.append({"role": "user", "content": content_prompt})

    try:
        azure_openai_client = await init_openai_client()
        response = await azure_openai_client.chat.completions.create(
            model=app_settings.azure_openai.model, messages=messages, temperature=1, max_tokens=64
        )
        title = response.choices[0].message.content
        return title
    except Exception as e:
        logging.exception("Exception while generating title", e)
        return messages[-2]["content"]


async def generate_title(conversation_messages) -> str:
    ## make sure the messages are sorted by _ts descending
    title_prompt = "Summarize the conversation so far into a 4-word or less title. Do not use any quotation marks or punctuation. Do not include any other commentary or description."

    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in conversation_messages
    ]
    messages.append({"role": "user", "content": title_prompt})

    try:
        azure_openai_client = await init_openai_client()
        response = await azure_openai_client.chat.completions.create(
            model=app_settings.azure_openai.model, messages=messages, temperature=1, max_tokens=64
        )
        title = response.choices[0].message.content
        return title
    except Exception as e:
        logging.exception("Exception while generating title", e)
        return messages[-2]["content"]


app = create_app()