import pypandoc

# Download Pandoc if it's not installed
try:
    pypandoc.download_pandoc()
    print("Pandoc successfully downloaded!")
except Exception as e:
    print(f"Error downloading Pandoc: {e}")

# Path to your markdown file
input_file = 'ocr_output.md'
output_file = 'output.epub'

# Convert markdown to EPUB
try:
    pypandoc.convert_file(input_file, 'epub', outputfile=output_file)
    print(f"EPUB file saved as '{output_file}'")
except Exception as e:
    print(f"Error during conversion: {e}")
