
from typing import Any, Dict, List
import requests
import os
import sys
root_folder = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_folder)
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import html2text
import base64
import tempfile
import json
from datetime import datetime
from Services.Connectors.iconnectorservice import IConnector
import logging
from inspect import getmembers, isfunction
#from GlobalDependencies import es
from bs4 import BeautifulSoup
class OutlookConnector():
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.tenant_id = os.getenv("TENANT_ID")
        delta = os.getenv("DELTA")
        Meta_fields = os.getenv('METADATA_FIELDS', '')
        self.metadata_fields = Meta_fields.split(",")
        Embedding_fields = os.getenv('EMBEDDING_FIELDS', '')  # Optional: Name of pages to exclude (if provided)
        self.embedding_fields = Embedding_fields.split(",")
        self.user_mail = os.getenv("UserMail")

    def get_access_token(self):
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Failed to retrieve access token: {response.text}")
            return None
    def get_attachments(self, attachment, email_id):
        """Extracts attachment content and metadata."""
        try:
            property = {
                "modifiedDate": attachment.get("lastModifiedDateTime"),
                "indexationDate": datetime.now(),
                "mailId": email_id,
                "fileSize": attachment.get("size", 0) / 1024,
                "file_name": attachment.get("name"),
                "fileExt": attachment.get("name", "").split(".")[-1],
                "type": "attachment"
            }

            if "contentBytes" in attachment:
                content_bytes = base64.b64decode(attachment["contentBytes"])
                property["text"] = content_bytes  # Directly store bytes
                return property
            else:
                logging.warning(f"Attachment {attachment['name']} has no contentBytes.")
                return None
        except Exception as e:
            logging.error(f"Error processing attachment {attachment.get('name')}: {e}")
            return None

    def fetch_emails(self):  # Added top_count parameter
        GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
        access_token = self.get_access_token()
        if not access_token:
            return

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": 'outlook.body-content-type="text"'
        }

        skip = 0
        total_fetched = 0  # Keep track of total fetched emails

        while(True):  # Loop until we reach the limit
             # Fetch max 10 at a time but respect the top limit.
            url = f"{GRAPH_API_ENDPOINT}/users/{self.user_mail}/mailFolders/Inbox/messages?$skip={skip}&top={10}"
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logging.error(f"Error fetching emails: {response.text}")
                break

            emails = response.json().get("value", [])
            if not emails:
                break  # No more emails to fetch

            for email in emails:
                try:
                    email_data = {
                        "from": email["from"]["emailAddress"]["address"],
                        "to": [i["emailAddress"]["address"] for i in email.get("toRecipients", [])],
                        "ccRecipients": [i["emailAddress"]["address"] for i in email.get("ccRecipients", [])],
                        "bccRecipients": [i["emailAddress"]["address"] for i in email.get("bccRecipients", [])],
                        "subject": email["subject"],
                        "createdDateTime": email["createdDateTime"],
                        "lastModifiedDateTime": email["lastModifiedDateTime"],
                        "receivedDateTime": email["receivedDateTime"],
                        "hasAttachments": email["hasAttachments"],
                        "id": email["id"],
                        "type": "email"
                    }

                    # Extract email body text
                    plain_text_content = email["body"]["content"]
                    email_data["body_content"] = re.sub(r"https?://\S+|www\.[a-zA-Z0-9]+\.[a-zA-Z]+", '', plain_text_content)
                    email_data["text"] = "Email: " + email_data["body_content"]

                    # Process attachments if present
                    if email["hasAttachments"]:
                        att_url = f"{GRAPH_API_ENDPOINT}/users/{self.user_mail}/messages/{email['id']}/attachments"
                        att_response = requests.get(att_url, headers=headers)
                        if att_response.status_code == 200:
                            attachments = att_response.json().get("value", [])
                            for attachment in attachments:
                                att_data = self.get_attachments(attachment, email["id"])
                                if att_data:
                                    yield att_data  # Yield attachment data separately
                     # Include subject if no attach
                    yield email_data  # Yield email data

                except Exception as e:
                    logging.error(f"Error processing email {email.get('id')}: {e}")

            # Increment the count of fetched emails
            skip += 10  # Increment skip by the number of emails we just processed.
 # Pagination contr
    def extract_fields(self,data, item):
        def recursive_get(dct, keys):
            """Navigate nested dict using keys."""
            for key in keys:
                dct = dct.get(key, {})
                if not isinstance(dct, (dict, list)):
                    return dct
            return dct

        file_metadata = {}
        for field in data:
            keys = field.split('.')
            file_metadata[field] = recursive_get(item, keys)

        return file_metadata
  
    def fetch_data(self, pipeline_instance):
        try:
            for email_data in self.fetch_emails():  # Fetch emails
                file_metadata = {}
                # Extract primary file details
                file_metadata['file_name'] = email_data.get('file_name')
                file_metadata['file_bytes'] = email_data.get('text') if email_data['type'] == 'attachment' else email_data.get('text')
              

                # Ensure embedding_fields and metadata_fields exist
                if self.embedding_fields or self.metadata_fields:
                    combined_data = {}

                    # Extract embedding fields
                    for field in self.embedding_fields:
                        if field in email_data:
                            combined_data["text"] = email_data[field]

                    # Extract metadata fields
                    metadata = {}
                    for field in self.metadata_fields:
                        if field in email_data:
                            metadata[field] = email_data[field]

                    if metadata:
                        combined_data["metadata"] = metadata

                    # Use combined_data if it contains valid data
                    if combined_data:
                        result = combined_data

                # Process the result through the pipeline
                pipeline_instance.process_record(file_metadata)

                # Print for debugging
                print(json.dumps(result, indent=4))

        except Exception as e:
            logging.error(f"An error occurred in fetch_data: {e}")
            
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        config = config['config']
        client_id = config.get('CLIENT_ID')
        client_secret = config.get('CLIENT_SECRET')
        tenant_id = config.get('TENANT_ID')
        user_mail = config.get('UserMail')
        embedding_fields = config.get('EMBEDDED_FIELD')
        metadata_fields = config.get('METADATA_FIELD')
      
        missing_fields = []

        if not client_id:
            missing_fields.append("client_id")
        if not client_secret:
            missing_fields.append("client_secret")
        if not tenant_id:
            missing_fields.append("tenant_id")

        embedding_fields = embedding_fields
        metadata_fields = metadata_fields

        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing fields: {', '.join(missing_fields)}",
                "error": True
            }

        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }
