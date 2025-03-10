** Note: These scripts were entirely generated with AI **

---

## Purpose

With the rapid advancement of AI, progress in OCR has also come a long way. With the announcement of an advanced OCR model, MistralAI allows us to extract the contents of PDF Files to a markdown file.

This repo contains two scripts, one that processes the specified PDF into markdown, and another which turns the markdown file into an ePub ready for reading.

Please note that although the result is readable, this is by no means a clean solution. It is however a solution which brings us much closer to cleaner conversion from PDF to ePub than anything I have tried before, and for the one who can overlook a small amount of visual clutter, this is a great step forward.

---

## Requirements

For this to work, you must 

1. Have the Python Requests Library installed, and it can be done using:

```
pip install requests
```

2. Have a free API Key from Mistral

---

## Usage

1. Place the PDF in question into the same directory as the scripts
2. Amend `01_Mistral_PDF_OCR.py` with your own Mistral Free API Key and the path to the PDF in question
3. Run `01_Mistral_PDF_OCR.py` using `python3 01_Mistral_PDF_OCR.py`, a markdown file will be generated
4. Run `02_ePub_Generator.py` using `python3 02_ePub_Generator.py` and an ePub file will be generated
