from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class DeletedItem(BaseModel):
    site_id: str
    list_id: str
    deleted_item_id: str

def notify_deleted_item(deleted_item: DeletedItem):
    # Placeholder function to handle notification
    print(f"Notification: Item with ID {deleted_item.deleted_item_id} deleted from list with ID '{deleted_item.list_id}' in site with ID '{deleted_item.site_id}'")

@app.post("/trigger")
async def handle_trigger(deleted_item: DeletedItem):
    # Your custom logic here
    try:
        # Notify about the deleted item
        notify_deleted_item(deleted_item)
        return {"message": "Notification sent successfully"}
    except Exception as e:
        # Handle errors
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
