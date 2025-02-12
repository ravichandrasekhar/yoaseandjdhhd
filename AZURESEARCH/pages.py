import fitz  # PyMuPDF

# Provide the file path to the PDF file
pdf_file_path = "C:\\Users\\ravichandrav\\Desktop\\file-example_PDF_1MB.pdf"

# Open the PDF file
pdf_document = fitz.open(pdf_file_path)

# Process each page
for page_num in range(pdf_document.page_count):
    page = pdf_document.load_page(page_num)
    print(f"Page {page_num + 1}:")
    
    # Extract text from the page
    page_text = page.get_text()
    
    if page_text:
        print(page_text)
    else:
        print("Error: Unable to extract text from the page.")
    
    print()

# Close the PDF document
pdf_document.close()
