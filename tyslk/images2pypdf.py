import PyPDF2
from PIL import Image

def extract_images_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    num_pages = len(pdf_reader.pages)
    
    images = []
    
    for page_num in range(num_pages):
        page = pdf_reader.pages[page_num]
        
        if '/XObject' in page['/Resources']:
            xObject = page['/Resources']['/XObject'].getObject()
            
            for obj in xObject:
                if xObject[obj]['/Subtype'] == '/Image':
                    size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                    data = xObject[obj].getData()
                    
                    if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                        mode = "RGB"
                    else:
                        mode = "P"

                    image = Image.frombytes(mode, size, data)
                    images.append(image)
    
    return images

# Example usage
if __name__ == "__main__":
    pdf_file_path = "C:\\Users\\ravichandrav\\Downloads\\monopoly.pdf"
    
    with open(pdf_file_path, "rb") as f:
        images = extract_images_from_pdf(f)
    
    for i, image in enumerate(images):
        image.show()  # Display or further process the extracted images
