from pydantic import BaseModel
from typing import List, Optional

class ChunkingConfig(BaseModel):
    chunking_strategy: str  
    max_tokens: Optional[int] = None  
    overlap_tokens: Optional[int] = None 

class ChunkingRequest(BaseModel):
    extracted_text: str
    config: ChunkingConfig

class ChunkingResponse(BaseModel):
    status: str
    chunks: List[str]
    error: Optional[str] = None