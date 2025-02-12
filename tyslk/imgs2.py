from unstructured.partition.pdf import partition_pdf
import os
import unstructured
from PIL import Image
import io
import base64
# Ensure the output directory is correct and exists
poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'
output_dir = "C:\\Users\\ravichandrav\\Desktop\\data\\extracted_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract images with detailed logging
raw_pdf_elements = partition_pdf(
    filename="C:\\Users\\ravichandrav\\Desktop\\DW251 etc._385930-03.pdf",
    strategy="hi_res",
    extract_images_in_pdf=True,
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=False,
    extract_image_block_output_dir="extracted_data"
)
print(raw_pdf_elements)
# Verify extraction output
# for i, element in enumerate(raw_pdf_elements):
#     # Check if the element is an Image
#     if isinstance(element, unstructured.documents.elements.Image ):
#         print(f"Found an Image element at index {i}")


# Find the first Image element in the list
for i,element in enumerate(raw_pdf_elements):
    if "unstructured.documents.elements.Image" in str(type(element)):
        image_element = element
        print(f"Found an Image element at index {i}")
        

# Get the base64 encoded image data
# image_data_base64 = image_element.metadata[image_base64]

# # Decode the base64 data to bytes
# image_data_bytes = base64.b64decode(image_data_base64)

# # Create a BytesIO object and load the image data
# image_data = io.BytesIO(image_data_bytes)
# image = Image.open(image_data)

# # Display the image
# image.show()
image_element = raw_pdf_elements[38]  # Replace this with the index of the Image element

# Get the base64 encoded image data
image_data_base64 = image_element.metadata['image_base64']

# Decode the base64 data to bytes
image_data_bytes = base64.b64decode(image_data_base64)

# Create a BytesIO object and load the image data
image_data = io.BytesIO(image_data_bytes)
image = Image.open(image_data)

# Display the image
image.show()