import fitz  # PyMuPDF

# Provide the file path to the PDF file
pdf_file_path = "C:\\Users\\ravichandrav\\Desktop\\file-example_PDF_1MB.pdf"

# Open the PDF file
pdf_document = fitz.open(pdf_file_path)

# Iterate through each page
for page_num in range(pdf_document.page_count):
    # Get the page
    page = pdf_document.load_page(page_num)
    print(f"Page {page_num + 1}:")
    
    # Extract text from the page
    page_text = page.get_text()
    
    # Split the page content into lines
    lines = page_text.split('\n')
    
    # Initialize variables to store paragraphs
    paragraphs = []
    current_paragraph = ''
    
    # Iterate through each line and concatenate consecutive lines into paragraphs
    for line in lines:
        line = line.strip()
        if line:  # Non-empty line
            current_paragraph += ' ' + line if current_paragraph else line
        else:  # Empty line, signifies end of paragraph
            if current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = ''
    
    # Add the last paragraph if it's not empty
    if current_paragraph:
        paragraphs.append(current_paragraph)
    
    # Print or process each paragraph
    for paragraph_num, paragraph in enumerate(paragraphs, start=1):
        print(f"Paragraph {paragraph_num}: {paragraph.strip()}")
        # Here you can store/process each paragraph as a separate record
    print()
