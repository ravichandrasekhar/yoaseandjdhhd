import requests

def search_documents(service_endpoint, index_name, query, api_version, admin_key):
    url = f"{service_endpoint}/indexes/{index_name}/docs?search={query}&queryType=full&api-version={api_version}"
    headers = {
        "api-key": admin_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        results = response.json()
        return results
    else:
        print(f"Failed to execute search query. Status code: {response.status_code}, Error: {response.text}")
        return None

def main():
    # Azure Search service endpoint, API key, and index name
    service_endpoint = ""
    admin_key = ""  # Replace with your actual admin key
    index_name = "sampleindex1"  # Make sure this is the correct index name
    query = "headset laptop mobilephone"
    api_version = "2020-06-30"

    # Perform search query
    search_results = search_documents(service_endpoint, index_name, query, api_version, admin_key)

    # Process search results
    if search_results:
        print("Search Results:")
        for result in search_results["value"]:
            print(result)
    else:
        print("No search results.")

if __name__ == "__main__":
    main()
