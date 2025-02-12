import openai
from transformers import T5ForConditionalGeneration, T5Tokenizer, BartForConditionalGeneration, BartTokenizer
from typing import Any, Dict, List
import os
import warnings
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
from rake_nltk import Rake
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from gensim import corpora
from gensim.models import LdaModel
import nltk
from typing import List, Tuple

class Summarizer:
    def summarize_chunk(self, text: str) -> str:
        """Abstract method to summarize a single chunk of text."""
        raise NotImplementedError("This method should be implemented by subclasses.")
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }


#
class T5Summarizer(Summarizer):
    def __init__(self):
        try:
            self.tokenizer = T5Tokenizer.from_pretrained("t5-small", clean_up_tokenization_spaces=True, legacy=False)
            self.model = T5ForConditionalGeneration.from_pretrained("t5-small")
        except Exception as e:
            raise RuntimeError(f"Error loading T5 model: {e}")

    def summarize_chunk(self, text: str) -> str:
        try:
            inputs = self.tokenizer(f"{text}", return_tensors="pt", max_length=512, truncation=True)
            summary_ids = self.model.generate(
                inputs["input_ids"],
                max_length=150,
                num_beams=4,
                early_stopping=True,
            )
            return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
        except Exception as e:
            raise RuntimeError(f"Error during T5 summarization: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class BARTSummarizer(Summarizer):
    def __init__(self):
        try:
            self.tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
            self.model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
        except Exception as e:
            raise RuntimeError(f"Error loading BART model: {e}")

    def summarize_chunk(self, text: str) -> str:
        try:
            inputs = self.tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
            summary_ids = self.model.generate(
                inputs["input_ids"], max_length=150, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True
            )
            return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        except Exception as e:
            raise RuntimeError(f"Error during BART summarization: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class SumySummarizer(Summarizer):
    def __init__(self, algorithm=LsaSummarizer, sentence_count: int = 5):
        super().__init__()
        self.algorithm = algorithm
        self.sentence_count = sentence_count

    def summarize_chunk(self, text: str) -> str:
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = self.algorithm()
            return " ".join(str(sentence) for sentence in summarizer(parser.document, self.sentence_count))
        except Exception as e:
            raise RuntimeError(f"Error during Sumy summarization: {e}")
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        } 
class BERTSummarizer(Summarizer):
    def __init__(self):
        """
        Initializes the BERT Summarizer using a pre-trained BERT model for extractive summarization.
        """
        super().__init__()
        try:
            # Initialize the pre-trained BERT model
            self.model = Summarizer()
        except Exception as e:
            raise (f"Error initializing BERT model: {e}")

    def summarize_chunk(self, text: str) -> str:
        """
        Summarize a single chunk of text using the BERT extractive summarization model.
        """
        try:
            # Generate the summary
            summary = self.model(text, ratio=0.2)  # ratio specifies the proportion of text to keep
            return summary.strip()
        except Exception as e:
            raise (f"Error during BERT summarization: {e}")
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }

class KeywordExtractor:
    def __init__(self, max_keywords=10):
        self.rake = Rake()
        self.max_keywords = max_keywords

    def summarize_chunk(self, chunk: str) -> List[str]:
        try:
            self.rake.extract_keywords_from_text(chunk)
            return self.rake.get_ranked_phrases()[:self.max_keywords]
        except Exception as e:
            raise RuntimeError(f"Error during keyword extraction: {e}")
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }
# Download NLTK resources if not already available
nltk.download("punkt")
nltk.download("stopwords")

class TopicModeler(Summarizer):
    def __init__(self, num_topics: int = 5, passes: int = 10, iterations: int = 100):
        """
        Initializes the LDA Topic Modeler with specified parameters.
        
        :param num_topics: Number of topics to extract.
        :param passes: Number of passes during training.
        :param iterations: Number of iterations during training.
        """
        self.num_topics = num_topics
        self.passes = passes
        self.iterations = iterations
        self.stop_words = set(stopwords.words("english"))

    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocesses the text by tokenizing and removing stopwords.
        
        :param text: The text to preprocess.
        :return: A list of processed tokens.
        """
        tokens = word_tokenize(text.lower())
        return [word for word in tokens if word.isalnum() and word not in self.stop_words]

    def summarize_chunk(self, text: str) -> List[Tuple[int, str]]:
        """
        Generates topic modeling results for a single chunk of text.
        
        :param chunk: The text chunk to process.
        :return: A list of topics with topic IDs and representative words.
        """
        try:
            # Preprocess the chunk
            processed_text = self.preprocess_text(text)
            
            # Create dictionary and corpus
            dictionary = corpora.Dictionary([processed_text])
            corpus = [dictionary.doc2bow(processed_text)]
            
            # Train the LDA model
            lda_model = LdaModel(corpus, num_topics=self.num_topics, id2word=dictionary,
                                 passes=self.passes, iterations=self.iterations, random_state=42)
            
            # Extract topics
            topics = lda_model.print_topics(num_words=5)  # Adjust the number of words per topic as needed
            return [(topic_id, topic_words) for topic_id, topic_words in topics]
        except Exception as e:
            raise RuntimeError(f"Error during topic modeling: {e}")
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
      
        return {
            "status": "success",
            "message": "Validation successful",
            "error": False
        }