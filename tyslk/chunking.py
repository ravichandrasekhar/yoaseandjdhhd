from typing import Dict, List,Any
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
from typing import Any, Dict, List
import re
from Services.Chunking.exception import ChunkingException
import os
# Load the spaCy model with error handling
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    raise ChunkingException(f"Failed to load spaCy model: {e}")

class Chunker:
    def chunk(self, text: str) -> List[str]:
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class ParagraphChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        """Chunk text by grouping sentences into paragraphs."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            doc = nlp(text)
            paragraphs, current_paragraph = [], []
            for sent in doc.sents:
                current_paragraph.append(sent.text.strip())
                # Separate paragraphs based on sentence-ending punctuation and line breaks
                if '\n' in sent.text or sent.text.endswith(('.', '!', '?')):
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []

            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            return paragraphs
        except Exception as e:
            raise ChunkingException(f"Error during paragraph chunking: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class PageChunker(Chunker):
    def __init__(self, page_tokens: List[str] = None) -> None:
        """Initialize with tokens for page separators."""
        self.page_tokens = page_tokens or []

    def chunk(self, text: str) -> List[str]:
        """Chunk text by pages using custom page markers."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")

        pages = [text]
        try:
            for token in self.page_tokens:
                pages = sum([re.split(token, page) for page in pages], [])
            return [page.strip() for page in pages if page.strip()]
        except Exception as e:
            raise ChunkingException(f"Error during page chunking: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["PAGE_TOKENS"]
       
        missing_fields = [field for field in required_fields if not config['config'].get(field)]
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
        
class SpecificTokenChunker(Chunker):
        def __init__(self, max_tokens: int):
            self.max_tokens = max(max_tokens, 1)  # Ensure at least 1 token per chunk

        def chunk(self, text: str) -> List[str]:
            """Chunk text into fixed-size token chunks without overlap."""
            if not text.strip():
                raise ChunkingException("Input text is empty or only contains whitespace.")
            
            words = text.split()
            return [' '.join(words[i:i + self.max_tokens]) for i in range(0, len(words), self.max_tokens)]

        def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
            required_fields = ["MAX_TOKENS"]
       
            missing_fields = [field for field in required_fields if not config['config'].get(field)]
            
            # If there are any missing fields, return an error message
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"{', '.join(missing_fields)} are required and must be positive integers.",
                    "error": True
                }

            # Return success if all checks pass
            return {
                "status": "success",
                "message": "Validation successful",
                "error": False
            }


class OverlappingTokenChunker(Chunker):
    def __init__(self, max_tokens: int, overlap_tokens: int):
        self.max_tokens = max(max_tokens, 1)  # Ensure at least 1 token per chunk
        self.overlap_tokens = max(overlap_tokens, 0)  # Non-negative overlap

    def chunk(self, text: str) -> List[str]:
        """Chunk text into fixed-size token chunks with overlap."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        
        words = text.split()
        step = max(self.max_tokens - self.overlap_tokens, 1)
        return [' '.join(words[i:i + self.max_tokens]) for i in range(0, len(words), step)]

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
             
            required_fields = ["MAX_TOKENS","OVERLAP_TOKENS"]
       
            missing_fields = [field for field in required_fields if not config['config'].get(field)]
            
            # If there are any missing fields, return an error message
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"{', '.join(missing_fields)} are required and must be positive integers.",
                    "error": True
                }

            # Return success if all checks pass
            return {
                "status": "success",
                "message": "Validation successful",
                "error": False
            }



class SentenceChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        """Chunk text into sentences."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            doc = nlp(text)
            return [sent.text.strip() for sent in doc.sents]
        except Exception as e:
            raise ChunkingException(f"Error during sentence segmentation: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }


class EntityChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        """Extract named entities from the text."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            doc = nlp(text)
            return [ent.text for ent in doc.ents]
        except Exception as e:
            raise ChunkingException(f"Error during entity extraction: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }


class SemanticChunker(Chunker):
    def __init__(self, max_len: int = 200):
        self.max_len = max_len

    def chunk(self, text: str) -> List[str]:
        """Chunk text semantically based on sentence lengths."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            doc = nlp(text)
            chunks, current_chunk = [], []
            for sent in doc.sents:
                current_chunk.append(sent.text)
                if len(' '.join(current_chunk)) > self.max_len:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            return chunks
        except Exception as e:
            raise ChunkingException(f"Error during semantic chunking: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
           
            required_fields = ["MAX_LEN"]
       
            missing_fields = [field for field in required_fields if not config['config'].get(field)]
            
            # If there are any missing fields, return an error message
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"{', '.join(missing_fields)} are required and must be positive integers.",
                    "error": True
                }

            # Return success if all checks pass
            return {
                "status": "success",
                "message": "Validation successful",
                "error": False
            }


class TopicBasedChunker(Chunker):
    def __init__(self, num_topics: int = 3):
        self.num_topics = num_topics

    def chunk(self, text: str) -> List[str]:
        """Chunk text based on topics using LDA."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            sentences = text.split('. ')
            vectorizer = CountVectorizer()
            sentence_vectors = vectorizer.fit_transform(sentences)

            lda = LatentDirichletAllocation(n_components=self.num_topics, random_state=42)
            lda.fit(sentence_vectors)

            topic_word = lda.components_
            vocabulary = vectorizer.get_feature_names_out()

            topics = [
                ", ".join([vocabulary[i] for i in topic.argsort()[:-6:-1]])
                for topic in topic_word
            ]

            chunks = []
            for i, sentence in enumerate(sentences):
                topic_assignment = lda.transform(vectorizer.transform([sentence]))
                topic_idx = np.argmax(topic_assignment)
                chunks.append(f"Topic {topic_idx + 1}: {topics[topic_idx]} - {sentence}")

            return chunks
        except Exception as e:
            raise ChunkingException(f"Error during topic-based chunking: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for TopicBasedChunker."""
       
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }
        
        
class ContentAwareChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        """Chunk text based on content markers or semantic relevance.""" 
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        try:
            chunks, current_chunk = [], []
            for sentence in text.split('. '):
                if len(' '.join(current_chunk)) > 200: 
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                current_chunk.append(sentence)
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            return chunks
        except Exception as e:
            raise ChunkingException(f"Error during content-aware chunking: {e}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for TopicBasedChunker."""
       
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class HierarchicalChunker(Chunker):
    def __init__(self, section_keywords=None):
        self.section_keywords = section_keywords or []

    def chunk(self, text: str) -> List[str]:
        # Implement the logic to split the text into sections based on section_keywords
        chunks = []
        for keyword in self.section_keywords:
            if keyword in text:
                # Extract the section based on keyword logic
                section = text.split(keyword, 1)[1]
                chunks.append(section)
        return chunks

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for TopicBasedChunker."""
       
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }


class KeywordBasedChunker(Chunker):
    def __init__(self,keywords: List[str] = None):
       self.keywords = keywords      
    def chunk(self, text: str) -> List[str]:
        """Chunk text based on specific keywords."""
        if not text.strip():
            raise ChunkingException("Input text is empty or only contains whitespace.")
        
        chunks, current_chunk = [], []
        for line in text.splitlines():
            if any(keyword in line for keyword in self.keywords):
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]  # Start a new chunk with the keyword line
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))  # Add the final chunk if non-empty
        return chunks
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for TopicBasedChunker."""
       
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }