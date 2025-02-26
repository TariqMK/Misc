import xml.etree.ElementTree as ET
from html import unescape
import os
import re

def find_xml_file():
    # Find the first XML file in the current directory (not subdirectories)
    for file in os.listdir():
        if file.endswith(".xml"):
            return file
    return None


def sanitize_filename(title):
    # Remove invalid filename characters and strip whitespace/newlines
    title = title.replace("\n", " ").strip()
    return re.sub(r'[\\/:*?"<>|]', '_', title)


def extract_posts(xml_file):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_posts")

    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Define the WordPress namespace (common in exports)
    ns = {'wp': 'http://wordpress.org/export/1.2/'}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for item in root.findall(".//item"):
        title = item.find("title").text or "Untitled"
        content = item.find("{http://purl.org/rss/1.0/modules/content/}encoded").text or ""
        post_date = item.find("{http://wordpress.org/export/1.2/}post_date").text or "Unknown Date"
        
        # Clean and sanitize title for filename
        sanitized_title = sanitize_filename(title)
        filename = f"{sanitized_title.replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Write post content to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n")
            f.write(f"Date: {post_date}\n\n")
            f.write(unescape(content))

    print(f"Posts extracted to: {output_dir}")


# Automatically find and run extraction on the first XML file found
xml_file = find_xml_file()
if xml_file:
    print(f"Found XML file: {xml_file}")
    extract_posts(xml_file)
else:
    print("No XML file found in the current directory.")
