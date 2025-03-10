import os
from mistralai import Mistral

# Add your API key here
API_KEY = "ENTER-API-KEY-HERE"

if not API_KEY:
    raise ValueError("Please add your Mistral API key to the 'API_KEY' variable.")

# Initialize the Mistral client
client = Mistral(api_key=API_KEY)

# Define the path to your local PDF
file_path = r"\path\to\file.pdf"
output_file = "ocr_output.md"

try:
    # Step 1: Upload the PDF to Mistral
    with open(file_path, "rb") as pdf_file:
        uploaded_pdf = client.files.upload(
            file={
                "file_name": os.path.basename(file_path),
                "content": pdf_file,
            },
            purpose="ocr"
        )

    # Step 2: Retrieve the signed URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    # Step 3: Process OCR on the PDF using the signed URL
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url
        }
    )

    # Debug print to see the structure of ocr_response (if needed)
    # print("OCR Response:", ocr_response)

    # Step 4: Save the OCR results to a markdown file
    with open(output_file, "w", encoding="utf-8") as md_file:
        for page in ocr_response.pages:  # Loop through the OCR pages
            # Extract the markdown content from each page
            page_content = f"## Page {page.index + 1}\n\n{page.markdown}\n\n"
            md_file.write(page_content)
            print(page_content)  # Optionally print to the console as well

    print(f"OCR results saved to '{output_file}'")

except FileNotFoundError:
    print(f"Error: File not found at '{file_path}'. Please check the path.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
