from bs4 import BeautifulSoup
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Optional, List


def convert_asciidoc_to_html(asciidoc_content):
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.asciidoc', delete=False) as temp_input:
        temp_input.write(asciidoc_content)
        temp_input_path = temp_input.name

    try:
        result = subprocess.run(
            ['asciidoctor', '-o', '-', temp_input_path],
            check=True,
            text=True,
            capture_output=True,
        )
        html_content = result.stdout
    finally:
        os.remove(temp_input_path)

    return html_content

def extract_urls_from_file(file_path, url_input_list=None):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

        # For HTML files, use BeautifulSoup to extract URLs from anchor tags
        if file_path.suffix.lower() == '.html':
            soup = BeautifulSoup(content, 'html.parser')
            urls = [a['href'] for a in soup.find_all('a', href=True, class_=lambda x: x != 'co') if not (a['href'].startswith('#') or a['href'].startswith('mailto:'))]
        elif file_path.suffix.lower() in ['.adoc', '.asciidoc']:
            # For AsciiDoc files, convert to HTML and extract URLs from the HTML content
            html_content = convert_asciidoc_to_html(content)
            soup = BeautifulSoup(html_content, 'html.parser')
            urls = [a['href'] for a in soup.find_all('a', href=True, class_=lambda x: x != 'co') if not (a['href'].startswith('#') or a['href'].startswith('mailto:'))]

        # Filter URLs to keep only those that are in url_input_list
        if url_input_list is not None:
            urls = [url for url in urls if url in url_input_list]

        return urls


def find_urls(
        filepaths: list[Path], 
        url_input_list: Optional[List[str]] = None
    ) -> tuple[dict[Path, list[str]], set[str]]:
    """
    Find URLs in a list of files.
    Returns a tuple (file_urls, all_urls): 
        file_urls: dictionary with filepaths as keys, lists of URLs as values
        all_urls: set of URLs across all files
    """
    file_urls = {}

    for filepath in filepaths:
        if url_input_list is not None:
            file_urls[filepath] = extract_urls_from_file(filepath, url_input_list)
        else:
            file_urls[filepath] = extract_urls_from_file(filepath)

    # Flatten and deduplicate URLs from all files
    all_urls = set(url for urls in file_urls.values() for url in urls)

    return file_urls, all_urls
