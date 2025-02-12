from fastapi import FastAPI, Query
from typing import List
import requests

app = FastAPI()

def search_documents(service_endpoint, index_name, query, api_version, admin_key):
    url = f"{service_endpoint}/indexes/{index_name}/docs?search={query}&queryType=full&api-version={api_version}"
    headers = {
        "api-key": admin_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to execute search query. Status code: {response.status_code}, Error: {response.text}"}

@app.get("/search/")
async def search(query: List[str] = Query(..., description="Search query terms")):
    service_endpoint = ""
    admin_key = ""  # Replace with your actual admin key
    index_name = "sampleindex1"  # Make sure this is the correct index name
    api_version = "2020-06-30"

    combined_query = " ".join(query)

    search_results = search_documents(service_endpoint, index_name, combined_query, api_version, admin_key)

    return search_results
