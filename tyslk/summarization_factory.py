from typing import Any, Dict, List
import os
from Factory.main_factory import INode
from Services.summarization.SummarizationBase import BaseSummarization
from Services.summarization.summarization import (
    BARTSummarizer,
    BERTSummarizer,
    KeywordExtractor,
    Summarizer,
    SumySummarizer,
    T5Summarizer,
    TopicModeler,
)
import json

class SummarizationFactory(INode):
    def __init__(self):
        self.model_name = os.getenv("MODEL_NAME")
        self.custom_prompt=os.getenv('CUSTOM_PROMPT')
        self.max_tokens=int(os.getenv('MAX_TOKENS'))
        self.summarizer = {
            # "gpt":GPTSummarizer(),
            "t5": T5Summarizer(),
            "bart": BARTSummarizer(),
            "sumy": SumySummarizer(),
            "bert": BERTSummarizer(),
            "keyword":KeywordExtractor(),
            "TopicModeler":TopicModeler()
        }
      

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration settings."""
        
        service_type:str = config['type']
        service_type = service_type.strip().lower()
        summarization_service:BaseSummarization=self.summarizer.get(service_type)
        if not summarization_service:
            return {
                "status": "error",
                "message": f"Unsupported summarization_type: {service_type}",
                "error": True
            }
        
        # Validate the configuration using the appropriate service
        return summarization_service.validate_config(config)

    def get_summarizer(self, model_name: str) -> Summarizer:
        summarizer_instance = self.summarizer.get(model_name)
        if not summarizer_instance:
            raise ValueError(f"Unknown summarizer model: {model_name}")
        return summarizer_instance

    def process_node(self, record: Dict) -> Dict:
      

        # Get summarizer instance
        summarizer = self.get_summarizer(self.model_name)
        text = record.get("text", "").strip()
        if not text:  # Handle empty text
            return {
                "status": "failed",
                "error": "Record text is empty or contains only whitespace.",
                "summarization": []
            }


        try:
            # Process the text using the chunker
            chunks = summarizer.summarize_chunk(text,self.max_tokens)
            if isinstance(chunks, str):
             summarization = [chunks]
            updated_record = record.copy()
            updated_record["chunks"] = summarization

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