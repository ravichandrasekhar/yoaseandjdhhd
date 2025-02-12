from pydantic import BaseModel
from PIL import Image
import io
import os
import pytesseract
poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'
class ImageExtractor:
    class InputSchema(BaseModel):
        InputSchema:str
       
    def process_image(image_content):
            """Extract and chunk text from an image file."""
            image = Image.open(io.BytesIO(image_content))
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            text = pytesseract.image_to_string(image)
            return text