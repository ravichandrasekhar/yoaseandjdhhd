from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTImage
import os

# Define a function to save raw image data
def save_raw_image_data(lt_image, output_dir):
    if lt_image.stream:
        raw_data = lt_image.stream.get_rawdata()
        if not raw_data:
            return

        file_name = f"{lt_image.name}.raw"
        file_path = os.path.join(output_dir, file_name)
        
        # Save the raw image data
        with open(file_path, 'wb') as f:
            f.write(raw_data)
        
        print(f"Raw image data saved: {file_path}")

# Path to the PDF file
pdf_path = 'D:\\imagext\\data\\Clouded Judgement 6.21.24 - by Jamin Ball.pdf'

# Output directory to save images
output_dir = 'C:\\Users\\ravichandrav\\Desktop\\data\\images1'
os.makedirs(output_dir, exist_ok=True)

# Extract pages and process them
for page_layout in extract_pages(pdf_path, laparams=LAParams()):
    for element in page_layout:
        if isinstance(element, LTImage):
            save_raw_image_data(element, output_dir)

print("Raw image data extracted and saved successfully.")
