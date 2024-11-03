import os
import re

def clean_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    lines = content.split("\n")
    new_lines = []
    last_bookmark_position = -1

    for i, line in enumerate(lines):
        if ("Your Bookmark" in line):
            new_lines.pop()
            last_bookmark_position = i
        if (last_bookmark_position == -1 or not i - last_bookmark_position < 4):
            new_lines.append(line)

    file_content = "\n".join(new_lines)
    return file_content


def parse_clippings(content):
    # A dictionary to store highlights by book title
    books = {}
    
    # Regular expression pattern to capture the book title, author, location, and highlight text
    pattern = r"(.*?) \((.*?)\)\n- (Your Highlight on .*? \| location .*?|Your Highlight at location .*?|Your Highlight on page .*?|Highlight on Page .*?)\n\n(.*?)\n=========="
        
    # Find all matches of the pattern in the file content
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"Found {len(matches)} highlights.")  # Shows how many highlights are captured
    
    # Loop through each match to organize the highlights
    for match in matches:
        book_title = match[0].strip().encode('utf-8').decode('utf-8-sig').strip()  # Remove BOM
        author = match[1].strip()  # Get the author
        highlight_source = match[2].strip()  # Get the highlight source information
        highlight_text = match[3].strip()  # Get the highlighted text
        
        # Separate page and location from the highlight source if available
        page_info = ''
        location_info = ''
        if 'page' in highlight_source.lower():
            page_info = highlight_source.split('|')[0].replace('Your Highlight on ', '').strip()
            location_info = highlight_source.split('|')[1].replace('location', '').strip()
        elif 'location' in highlight_source.lower():
            location_info = highlight_source.split('|')[0].replace('Your Highlight at ', '').strip()
        
        # Add highlight to the respective book in the dictionary
        if book_title not in books:
            books[book_title] = []  # Create a new list for a new book
        books[book_title].append((highlight_text, author, page_info, location_info))  # Append the highlight to the book's list
    
    return books

def save_highlights(books):
    # Create an output directory if it doesn't exist
    output_dir = 'Highlights_by_Book'
    os.makedirs(output_dir, exist_ok=True)
    
    total_highlights = 0
    book_highlights = {}

    # Write each book's highlights to a separate file
    for book_title, highlights in books.items():
        # Strip everything after the first colon for both file naming and display purposes
        stripped_title = book_title.split(':')[0].strip()  # Ensure no leading/trailing spaces
        file_name = re.sub(r'[<>:"/\\|?*]', '', stripped_title) + '.txt'
        file_path = os.path.join(output_dir, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            for i, (highlight_text, author, page_info, location) in enumerate(highlights, start=1):  # Start numbering from 1
                # Write the formatted highlight without the timestamp
                file.write(f"{i}. {highlight_text}\n\t<{book_title}>({author}) Your Highlight on {page_info} | location {location}\n\n")
        
        num_highlights = len(highlights)
        total_highlights += num_highlights
        book_highlights[stripped_title] = num_highlights  # Store the number of highlights for this book
        print(f"Highlights for '{book_title}' saved to {file_path}")

    # Display the highlights summary in a formatted table
    max_title_length = max(len(title) for title in book_highlights.keys())  # Determine the max title length
    header = "Highlights"
    header_space = 15  # Fixed space for the highlights column

    # Print the formatted table
    print("\n" + " " * (max_title_length + 1) + f"| {header}")  # Align the header with the longest title
    print("-" * (max_title_length + header_space + 1))  # Adjust the line length for the separator

    # Print each book's highlights in a uniform table format
    for title, count in book_highlights.items():
        print(f"{title.ljust(max_title_length)} | {str(count).rjust(5)}")  # Added 1 space for slight padding

    print("-" * (max_title_length + header_space + 1))  # Same line length for total separation
    print(f"{'TOTAL'.ljust(max_title_length)} | {str(total_highlights).rjust(5)}")

# Set the file path to My Clippings.txt in the same directory as the script
file_path = 'My Clippings.txt'

# Parse the clippings and save them by book
books = parse_clippings(clean_file(file_path))
save_highlights(books)
