from unstructured.partition.pdf import partition_pdf
import os

# Set environment paths for external tools if needed
poppler_path = r'D:\\configurations\\poppler-0.68.0 (1)\\poppler-0.68.0\\bin'
tesseract_path = r'D:\\configurations\\test\\tesseract.exe'

# Update PATH environment variable to include necessary paths
os.environ['PATH'] = poppler_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = f'{os.path.dirname(tesseract_path)};{os.environ["PATH"]}'

# Define the output directory for extracted images
output_dir = "D:\\extracted_images1"

# Ensure the output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Path to the PDF file
pdf_path = "C:\\Users\\ravichandrav\\Desktop\\DW251 etc._385930-03.pdf"

# Check if the PDF file exists
if not os.path.exists(pdf_path):
    print(f"PDF file not found: {pdf_path}")
else:
    # Extract elements from the PDF
    elements = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",
        extract_image_block_types=["Image", "Table"],
        extract_image_block_to_payload=True,
        extract_image_block_output_dir=output_dir,
    )

    # Print extracted elements for debugging
    for element in elements:
        print(element)

    # Verify if any images were extracted
    extracted_images = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
    
    if extracted_images:
        print("Images have been successfully extracted and saved to:", output_dir)
        print("Extracted images:", extracted_images)
    else:
        print("No images were extracted or saved.")
