from fastapi import HTTPException
import requests
# from extraction.extraction import ExtractionData
# from sharepoint.indexation import IndexingData
import os

from extractors.formats.csvExtractor import CsvExtractor
from extractors.formats.docxExtractor import DocxExtractor
from extractors.formats.execelExtractor import ExecelExtractor
from extractors.formats.pdfExtractor import PdfExtractor
from extractors.formats.textExtractor import TextExtractor
class Sharepoint:
    def __init__(self, config):
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.tenant_id = config['Tenant_id']  # Fixed key name
        self.access_token = config['access_token']
        self.site_url = config['site_url']
        self.drive_urls = config['drive_urls']
        self.list_urls = config['list_urls']
        self.page_urls = config['page_urls']
        self.configuration = config['configuration']
        self.folder_id=config['folder_id']
        # self.fileprocessor = ExtractionData()
        # self.indexing = IndexingData(config)
       
    def authenticate(self):
        token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()
        return response.json()['access_token']

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
   
    
    def get_sharepoint_id(self, site_url):
        parts = site_url.split('/')
        hostname = parts[2]
        site_path = '/'.join(parts[4:])
        graph_url = f'https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_path}'

        response = requests.get(graph_url, headers=self.get_headers())
        if response.status_code == 200:
            site_info = response.json()
            return site_info['id']
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to retrieve site information: {response.text}")

    def get_sharepoint_list_data(self, list_id, site_id):
        try:
            schema_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
          
            response = requests.get(schema_url, headers=self.get_headers())
            if response.status_code == 200:
                schema_data = response.json()
                fields_to_expand_and_index = [column["name"] for column in schema_data["value"]]
                select_fields = ','.join(fields_to_expand_and_index)
                url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields(select={select_fields})"
                response = requests.get(url, headers=self.get_headers())
                if response.status_code == 200:
                    data = response.json()
                    return data.get('value', []), fields_to_expand_and_index
                else:
                    raise HTTPException(status_code=response.status_code, detail=f"Failed to retrieve data from SharePoint list. Status code: {response.status_code}")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to retrieve schema from SharePoint list. Status code: {response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching data from SharePoint list: {str(e)}")

    def get_all_sharepoint_lists(self, site_id):
        try:
            lists_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
            
            response = requests.get(lists_url, headers=self.get_headers())
            print("headers",self.get_headers())
            if response.status_code == 200:
                lists_data = response.json().get("value", [])
                all_lists_data = []
                for list_item in lists_data:
                    list_id = list_item.get("id")
                    list_data, fields = self.get_sharepoint_list_data(list_id, site_id)
                    all_lists_data.append({"list_id": list_id, "list_data": list_data, "fields": fields})
                return all_lists_data
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to retrieve lists from SharePoint site. Status code: {response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching lists from SharePoint site: {str(e)}")

    def get_list_id_from_url(self, list_url, site_id):
        list_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
        list_response = requests.get(list_endpoint, headers=self.get_headers())
        if list_response.status_code == 200:
            lists_data = list_response.json().get("value", [])
            for sp_list in lists_data:
                if sp_list.get("webUrl") == list_url:
                    return sp_list.get("id")
            return None
        else:
            raise HTTPException(status_code=list_response.status_code, detail=f"Failed to retrieve lists information: {list_response.text}")

    def get_item_permissions(self, item_id, list_id, site_id):
        try:
            permissions_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{item_id}/driveItem/permissions"
            response = requests.get(permissions_url, headers=self.get_headers())
            permissions = []
            
            if response.status_code == 200:
                permissions_data = response.json().get("value", [])
                for permission_data in permissions_data:
                    granted_to = permission_data.get("grantedTo", None)
                    if granted_to:
                        if "user" in granted_to:
                            user_or_group = granted_to["user"].get("displayName", "N/A")
                            permissions.append(user_or_group)
                        elif "group" in granted_to:
                            user_or_group = granted_to["group"].get("displayName", "N/A")
                            permissions.append(user_or_group)
            return permissions
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching permissions for item {item_id}: {str(e)}")

    def get_drive_id(self, site_id):
        drive_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        print("drive",drive_endpoint)
        
        drive_response = requests.get(drive_endpoint, headers=self.get_headers())
        
        if drive_response.status_code == 200:
            return drive_response.json().get("value", [])
        else:
            raise HTTPException(status_code=drive_response.status_code, detail=f"Failed to retrieve drives information: {drive_response.text}")

    def get_drive_id_from_url(self, drive_url, site_url):
         site_id = self.get_sharepoint_id(site_url)
        # print("Site ID:", site_id)
         if not site_id:
            return None
         drive_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
         drive_response = requests.get(drive_endpoint, headers=self.get_headers())
         if drive_response.status_code == 200:
            drives_data = drive_response.json().get("value", [])
            for drive in drives_data:
                if drive.get("webUrl") == drive_url:
                    return drive.get("id")
            return None
         else:
            raise HTTPException(status_code=drive_response.status_code, detail=f"Failed to retrieve drives information: {drive_response.text}")

    def get_sharepoint_items(self, folder_id, drive_id):
    
        try:
            if folder_id:
                url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}/children"
            
            else:
                url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"

          
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                data = response.json()['value']
                
                return data
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to retrieve items from SharePoint drive.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching items from SharePoint drive: {str(e)}")

    def download_sharepoint_file(self, file_id, drive_id):
        try:
            content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
           
            response = requests.get(content_url, headers=self.get_headers())
            if response.status_code == 200:
                return response.content
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to download file with ID '{file_id}'")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error downloading file from SharePoint drive: {str(e)}")

    def get_permissions(self, drive_id, file_id):
        permissions_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/permissions"
     
        response = requests.get(permissions_url, headers=self.get_headers())
        permissions = []
        if response.status_code == 200:
            permissions_data = response.json().get("value", [])
            for permission_data in permissions_data:
                granted_to = permission_data.get("grantedTo", None)
                if granted_to:
                    if "user" in granted_to:
                        user_or_group = granted_to["user"].get("displayName", "N/A")
                        permissions.append(user_or_group)
                    elif "group" in granted_to:
                        user_or_group = granted_to["group"].get("displayName", "N/A")
                        permissions.append(user_or_group)
        return permissions
        from extraction.extraction import ExtractionData
        file_extension = os.path.splitext(file_name)[1].lower()
        extractors = {
            ".docx": ExtractionData.process_docx,
            ".pdf": ExtractionData.process_pdf,
            ".txt": ExtractionData.process_txt,
            ".xlsx": ExtractionData.process_xlsx,
            ".xls": ExtractionData.process_xlsx,
            ".csv": ExtractionData.process_csv
        }
        content_str = extractors.get(file_extension, ExtractionData.extract_text_from_other)(file_content)

    def get_sharepoint_pages(self):
        results = []
        for page_url in self.page_urls:
            page_id = self.get_page_id_from_url(page_url)
            if page_id:
                page_data = self.get_page_data(page_id)
                results.append(page_data)
        return results

    def get_page_id_from_url(self, page_url):
        site_id = self.get_sharepoint_id(self.site_url)
        pages_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/pages"
        
        pages_response = requests.get(pages_endpoint, headers=self.get_headers())
        if pages_response.status_code == 200:
            pages_data = pages_response.json().get("value", [])
            for page in pages_data:
                if page.get("webUrl") == page_url:
                    return page.get("id")
            return None
        else:
            raise HTTPException(status_code=pages_response.status_code, detail=f"Failed to retrieve pages information: {pages_response.text}")

    def get_page_data(self, page_id):
        page_endpoint = f"https://graph.microsoft.com/v1.0/sites/{self.site_url}/pages/{page_id}"
        page_response = requests.get(page_endpoint, headers=self.get_headers())
        if page_response.status_code == 200:
            return page_response.json()
        else:
            raise HTTPException(status_code=page_response.status_code, detail=f"Failed to retrieve page data: {page_response.text}")

    def process_data(self):
        results = []
     
        if self.configuration == "list":
            if self.list_urls and self.site_url:
                for site_url in self.site_url:
                    print("Site_url:", site_url)
                    sharepoint_site_id = self.get_sharepoint_id(site_url)
                    for list_url in self.list_urls:
                        list_id = self.get_list_id_from_url(list_url, site_url, self.access_token)
                        if not list_id:
                            continue
                        print(f"List ID from {site_url}:", list_id)
                        list_data, fields = self.get_sharepoint_list_data(list_id, sharepoint_site_id, self.access_token)
                        if not list_data:
                            raise HTTPException(status_code=404, detail=f"No items found in the SharePoint list '{list_url}'.")

                        all_documents = []
                        for list_item in list_data:
                            document = {"id": f"{list_id}_{list_item['id']}"}
                            fields_data = list_item.get('fields', {})
                            if not isinstance(fields_data, dict):
                                print(f"Unexpected fields data structure for list_item {list_item['id']}: {fields_data}")
                                continue
                            for field in fields:
                                rexgufield = self.indexing.regularexpression(field)
                                document[rexgufield] = str(fields_data.get(field, ''))
                            all_documents.append(document)

                        if all_documents:
                            self.indexing.index_documents_to_azure_search(all_documents, list_id, self.access_token, sharepoint_site_id, list_id, self.index_name)
                        results.append({'list_data': list_data})

            elif self.site_url:
                for site_url in self.site_url:
                    sharepoint_site_id = self.get_sharepoint_id(site_url)
                    all_lists_data = self.get_all_sharepoint_lists(sharepoint_site_id)
                    if not all_lists_data:
                        raise HTTPException(status_code=404, detail="No lists found in the SharePoint site.")
                    
                    all_documents = []
                    for list_item in all_lists_data:
                        list_id = list_item['list_id']
                        for list_data in list_item['list_data']:
                            document = {"id": f"{list_id}_{list_data['id']}"}
                            fields_data = list_data.get('fields', {})
                            if not isinstance(fields_data, dict):
                                print(f"Unexpected fields data structure for list_item {list_data['id']}: {fields_data}")
                                continue
                            for field in list_item['fields']:
                                rexgufield = self.regularexpression(field)
                                document[rexgufield] = str(fields_data.get(field, ''))
                            all_documents.append(document)

                    if all_documents:
                        self.indexing.index_documents_to_azure_search(all_documents, list_id, self.access_token, sharepoint_site_id, list_id, self.index_name)
                    results.append({"all_lists_data": all_lists_data})

        elif self.configuration == "drive":
            all_drive_items = []
            if self.drive_urls and self.site_url:
                for site_url in self.site_url:
                    sharepoint_site_id = self.get_sharepoint_id(site_url)
                    print("sharepoint_site_id",sharepoint_site_id)
                    for drive_url in self.drive_urls:
                        drive_id = self.get_drive_id_from_url(drive_url, site_url)
                        print("drive_id",drive_id)
                        if not drive_id:
                            continue
                        if self.folder_id:
                            drive_items = self.get_sharepoint_items(self.folder_id, drive_id)
                            for item in drive_items:
                                if item.get("file"):
                                    file_id = item["id"]
                                    file_name = item["name"]
                                    file_content = self.download_sharepoint_file(file_id, drive_id)
                                    file_extension = os.path.splitext(file_name)[1].lower()
                                    extractors = {
                                        ".docx": DocxExtractor.process_docx,
                                        ".pdf": PdfExtractor.process_pdf,
                                        ".txt": TextExtractor.process_txt,
                                        ".xlsx": ExecelExtractor.process_xlsx,
                                        ".xls": ExecelExtractor.process_xlsx,
                                        ".csv": CsvExtractor.process_csv
                                    }
                                    content_str = extractors.get(file_extension)(file_content)

                            print("Drive items: in if part", drive_id)
                        else:
                            drive_items = self.get_sharepoint_items( None, drive_id)
                            print("Drive items: in else part", drive_id)
                            all_drive_items.append({"drive_items": drive_items})

                    fields = ["content", "weburl", "fileName", "folderName"]
                    self.indexing.index_drive_folder(drive_id)
                    return {"drive_items": all_drive_items}

            elif self.site_url:
                for site_url in self.site_url:
                    drives = self.get_drive_id(site_url)
                    print("Drives:", drives)
                    all_drive_items = []
                    for drive in drives:
                        drive_id = drive["id"]
                        
                        if self.folder_id:
                            drive_items = self.get_sharepoint_items(self.folder_id, drive_id)
                            print("Drive items: in if part", drive_id)
                        else:
                            drive_items = self.get_sharepoint_items(None, drive_id)
                            print("Drive items: in else part", drive_id)
                        all_drive_items.append({"drive_id": drive_id, "drive_items": drive_items})
                    results.append({"drive_items": all_drive_items})
                fields = ["content", "weburl", "fileName", "folderName"]
                self.indexing.index_drive_folder(drive_id, self.access_token)

            else:
                raise HTTPException(status_code=400, detail="Drive ID is required for 'drive' configuration.")

        elif self.configuration == "pages":
            all_documents = []
            if self.site_url and self.pages_urls:
                for site_url in self.site_url:
                    print("Site url:", site_url)
                    sharepoint_site_id = self.get_sharepoint_id(site_url, self.access_token)
                    for page_url in self.pages_urls:
                        page_id = self.get_page_id_from_url(page_url, site_url, self.access_token)
                        if not page_id:
                            continue
                        print("Page id:", page_id)
                        pages = self.get_sharepoint_pages(sharepoint_site_id, self.access_token)
                        for page in pages:
                            document = {"id": page_id}
                            all_documents.append(document)

                fields = ["webUrl", "title", "description"]
                self.indexing.index_sharepoint_pages(sharepoint_site_id, self.access_token)
                return {"all_documents": all_documents}

            elif self.site_url:
                for site_url in self.site_url:
                    sharepoint_site_id = self.get_sharepoint_id(site_url, self.access_token)
                    pages = self.get_sharepoint_pages(sharepoint_site_id, self.access_token)
                    for page in pages:
                        document = {"id": page["id"]}
                        all_documents.append(document)

                fields = ["webUrl", "title", "description"]
                self.indexing.index_sharepoint_pages(sharepoint_site_id, self.access_token, self.index_name)

            else:
                raise HTTPException(status_code=400, detail="SharePoint site URL is required for 'pages' configuration.")

        else:
            raise HTTPException(status_code=400, detail="Invalid configuration type. Must be 'list', 'drive', or 'pages'.")

        return results

        
