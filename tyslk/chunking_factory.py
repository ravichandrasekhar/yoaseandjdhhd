from typing import Any, Dict, List
from Services.Chunking import chunking
from Services.Chunking.exception import ChunkingException
from Services.Chunking.base import BaseChunker
from Services.Chunking.chunking import (
    Chunker, ContentAwareChunker, EntityChunker, HierarchicalChunker,
    KeywordBasedChunker, OverlappingTokenChunker, PageChunker,
    ParagraphChunker, SemanticChunker, SentenceChunker,
    SpecificTokenChunker, TopicBasedChunker
)
from .main_factory import INode
import os
import json

class ChunkingFactory(INode):
    def __init__(self):
        # Load configuration from environment variables
        self.chunking_strategy = os.getenv("CHUNKING_STRATEGY", "").lower()
        self.max_tokens = os.getenv("MAX_TOKENS", 0)
        page_tokens_raw = os.getenv("PAGE_TOKENS", "")  # Read the raw tokens string

        # Split tokens by commas and clean up any extra spaces
        self.page_tokens = [token.strip() for token in page_tokens_raw.split(',')] if page_tokens_raw else None
        self.max_tokens = int(self.max_tokens) if self.max_tokens is not None else None
        self.overlap_tokens = os.getenv("OVERLAP_TOKENS", 0)
        self.overlap_tokens = int(self.overlap_tokens) if self.overlap_tokens is not None else None
        self.max_len = os.getenv("MAX_LEN", 0)
        self.max_len = int(self.max_len) if self.max_len is not None else None
        section_keywords = ["Introduction", "Overview", "Methods", "Conclusion"]
        keywords = ["Introduction", "Overview", "Conclusion", "Methods", "Challenges"]
        self.strategies
        # Define chunking strategies
        self.strategies = {
            "paragraph": ParagraphChunker(),
            "page": PageChunker(self.page_tokens),  # Conditional initialization
            "sentence": SentenceChunker(),
            "specific tokens": SpecificTokenChunker(self.max_tokens),
            "specific tokens with overlap": OverlappingTokenChunker(self.max_tokens, self.overlap_tokens),
            "entity": EntityChunker(),
            "semantic": SemanticChunker(self.max_len),
            "content_aware": ContentAwareChunker(),
            "keyword_based": KeywordBasedChunker(keywords=keywords),
            "topic_based": TopicBasedChunker(),
            "hierarchical": HierarchicalChunker(section_keywords=section_keywords)
        }

      
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration settings."""
        
        chunking_type = config['type'].lower()
        chunking_service:BaseChunker=self.strategies.get(chunking_type)
        if not chunking_service:
            return {
                "status": "error",
                "message": f"Unsupported chunking_type: {chunking_type}",
                "error": True
            }
        
        # Validate the configuration using the appropriate service
        return chunking_service.validate_config(config)


    def get_chunker(self, strategy: str) -> Chunker:
        """Get the appropriate chunker based on the strategy."""
        chunker_factory = self.strategies.get(strategy)
        if not chunker_factory:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

        # Use the factory to create the chunker instance
        return chunker_factory

    def process_node(self, record: Dict):
        """Process a single record and return chunked results with metadata."""
        print("chunking node starting")
        strategy = self.chunking_strategy  # Get strategy directly from the instance variable
        chunker = self.get_chunker(strategy)

        # Extract text from the record
        text = record.get("text", "").strip()

        if not text:  # Handle empty text
            return {
                "status": "failed",
                "error": "Record text is empty or contains only whitespace.",
               
            }

        try:
            # Process the text using the chunker
            chunks = chunker.chunk(text)
            updated_record = record.copy()
            updated_record["chunks"] = chunks
            return {
                "status": "success",
                "record": updated_record,
                "error": None
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": True,
                "message":str(e),
               
            }