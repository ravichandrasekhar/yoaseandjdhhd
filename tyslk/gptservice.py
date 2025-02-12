from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import uvicorn
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

app = FastAPI()

origins = [
    "http://localhost:4200",
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache to store past questions
cache = {
    "past_questions": []
}

client = AzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

# Azure Search client setup
service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
admin_key = os.getenv("AZURE_SEARCH_KEY")
credential = AzureKeyCredential(str(admin_key))
index_name = os.getenv("AZURE_SEARCH_INDEX")
search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=credential)

# Azure Blob Storage setup


def truncate_text(text, max_length):
    """Truncate text to ensure it doesn't exceed the max_length."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

@app.post("/search")
def search(req_body: dict):
    query = req_body.get("query")

    global cache
    past_questions = cache["past_questions"]

    if query not in past_questions:
        past_questions.append(query)

    if len(past_questions) > 5:
        past_questions.pop(0)

    try:
        if not isinstance(query, str):
            raise ValueError("Query must be a string")

        # Generate embedding for the query
        try:
            embedding = client.embeddings.create(input=query, model="text-embedding-ada-002").data[0].embedding
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in embedding creation: {e}")

        # Perform vector search
        vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=3, fields="contentVector", exhaustive=True)
        results = search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=["id", "content"],
            top=3
        )

        result_data = []
        for result in results:
            result_data.append({
                "id": result["id"],
                "content": result["content"],
               
            })

        # Generate the prompt with correct image references
        concatenated_results = '\n'.join([
            f"Result {i+1}: Content: {res['content']})"
            for i, res in enumerate(result_data)
        ])

        last_five_questions = "\n".join(past_questions)
        
        prompt = f'''
You are an assistant tasked with providing a response based on the top 3 search results for a given query. Use the following information to generate a response:

=========
CURRENT QUERY: {query}
=========
PAST QUESTIONS:
{last_five_questions}
=========
TOP 3 RESULTS:
{concatenated_results}
=========
Based on the top 3 results and the context of the current and past questions, generate a relevant and insightful response. Provide the image references used for generating this response.
'''

        # Truncate the prompt if necessary
        max_prompt_length = 2048
        prompt = truncate_text(prompt, max_prompt_length)

        try:
            response = client.chat.completions.create(
                model="gpt-35-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            output = response.choices[0].message.content
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating response: {e}")

        # Return the response and exact image references from the search results
        return {
            "response": output,
              
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)