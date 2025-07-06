#!/usr/bin/env python3
import os
import re
import shutil
import markdown
from pathlib import Path

# Define paths
docs_dir = Path('/Users/dhani/GitHub/dpk/rsw/docs')
html_docs_dir = Path('/Users/dhani/GitHub/dpk/rsw/html_docs')
img_dir = docs_dir / 'img'
html_img_dir = html_docs_dir / 'img'

# Ensure img directory exists
html_img_dir.mkdir(exist_ok=True)

# Copy all images from docs/img to html_docs/img
for img_file in img_dir.glob('*'):
    if img_file.is_file():
        shutil.copy2(img_file, html_img_dir / img_file.name)
        print(f"Copied {img_file.name} to {html_img_dir}")

# Read the HTML template
with open(html_docs_dir / 'template.html', 'r') as f:
    template = f.read()

# Function to convert markdown to HTML
def convert_md_to_html(md_file, html_file, title):
    # Read markdown content
    with open(md_file, 'r') as f:
        md_content = f.read()
    
    # Convert relative markdown links to HTML links
    md_content = re.sub(r'\[([^\]]+)\]\(\.\/([^)]+)\.md\)', r'[\1](\2.html)', md_content)
    
    # Convert all image links to use the img directory
    md_content = re.sub(r'!\[([^\]]+)\]\(\./img/([^)]+)\)', r'![\1](./img/\2)', md_content)
    md_content = re.sub(r'!\[([^\]]+)\]\(\./images/([^)]+)\)', r'![\1](./img/\2)', md_content)
    
    # Convert markdown to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Insert HTML content into template
    page_html = template.replace('CONTENT_PLACEHOLDER', html_content)
    page_html = page_html.replace('<title>RSW Documentation</title>', f'<title>RSW Documentation - {title}</title>')
    
    # Highlight the current page in the navigation
    page_name = html_file.stem
    page_html = page_html.replace(f'<a href="{page_name}.html">', f'<a href="{page_name}.html" class="active">')
    
    # Write HTML file
    with open(html_file, 'w') as f:
        f.write(page_html)
    
    print(f"Converted {md_file.name} to {html_file.name}")

# Convert each markdown file to HTML
md_files = [
    {'file': 'index.md', 'title': 'Home'},
    {'file': 'getting-started.md', 'title': 'Getting Started'},
    {'file': 'djinni-assistant.md', 'title': 'Djinni Assistant'},
    {'file': 'datapuur.md', 'title': 'DataPuur'},
    {'file': 'kginsights.md', 'title': 'KGInsights'},
    {'file': 'api-reference.md', 'title': 'API Reference'},
]

for md_file_info in md_files:
    md_path = docs_dir / md_file_info['file']
    if md_path.exists():
        html_path = html_docs_dir / (md_path.stem + '.html')
        convert_md_to_html(md_path, html_path, md_file_info['title'])
    else:
        print(f"Warning: {md_path} does not exist")

# Create an index.html file if it doesn't exist (redirect to home.html)
index_html = html_docs_dir / 'index.html'
if not index_html.exists():
    with open(index_html, 'w') as f:
        f.write('''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=index.html">
</head>
<body>
    <p>Redirecting to <a href="index.html">index.html</a>...</p>
</body>
</html>''')
    print("Created redirect index.html")

print("Conversion complete!")
