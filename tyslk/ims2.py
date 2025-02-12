from unstructured.partition.pdf import partition_pdf
import os
import unstructured

# Ensure the output directory is correct and exists
poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'
output_dir = "D:\\extracted_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract images with detailed logging
raw_pdf_elements = partition_pdf(
    filename="C:\\Users\\ravichandrav\\Downloads\\NA484468_CMCS300-T2-NA.pdf",
    strategy="hi_res",
    extract_images_in_pdf=True,
    extract_image_block_types=["Image", "Table"],
    extract_image_block_to_payload=False,
    extract_image_block_output_dir=output_dir
)

# Verify extraction output and save images
for i, element in enumerate(raw_pdf_elements):
    # Check if the element is an Image
    if isinstance(element, unstructured.documents.elements.Image):
        image_path = element.image_path
        image_filename = os.path.join(output_dir, f"image_{i}.png")
        
        if os.path.exists(image_path):
            os.rename(image_path, image_filename)
            print(f"Saved image {i}: {image_filename}")
        else:
            print(f"Image path {image_path} does not exist for element {i}")