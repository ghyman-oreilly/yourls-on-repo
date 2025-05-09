import os
import logging
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
import tempfile
import requests
import time
from yourls import YOURLSClient


logger = logging.getLogger(__name__)


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


def shorten_url(original_url, yourls: YOURLSClient):
    error_message = None
    shorturl = None
    
    try:
        shorturl = yourls.shorten(original_url)
        shorturl = shorturl.shorturl # obtain shorturl property from ShortenedURL
    except requests.HTTPError as exc:
        error_message = f"HTTPError: {exc}"
    except requests.exceptions.RequestException as exc:
        error_message = f"RequestException: {exc}"
    except yourls.exceptions.YourlsError as exc:
        error_message = f"YOURLS Error: {exc}"
    except yourls.exceptions.YourlsClientError as exc:
        error_message = f"YOURLS Client Error: {exc}"
    except yourls.exceptions.YourlsServerError as exc:
        error_message = f"YOURLS Server Error: {exc}"
    except yourls.exceptions.YourlsInvalidURLException as exc:
        error_message = f"Invalid URL: {exc}"
    except Exception as exc:
        error_message = f"An unexpected error occurred: {exc}" 
    if error_message is not None:
        logger.error(error_message)

    return shorturl


def update_file_content(filepath: Path, replacements: list[tuple[str, str]]):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()

    # Make replacements only for exact matches
    for original_url, shortened_url in replacements:
        original_url = original_url.replace('&', '&amp;')  # Replace '&' with '&amp;' (re-escaping the '&' that YOURLs unescaped)
        content = content.replace(original_url, shortened_url) # TODO: this sometimes results in a buggy replacement of partial URLs

    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)


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
        url_input_list: list[str] | None = None
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
    

def shorten_urls(file_urls: dict, all_urls: set, yourls_url, yourls_key):
    """
    Shorten urls and return a dict of filepaths and URLs.
    """
    yourls = YOURLSClient(yourls_url, signature=yourls_key)
    
    filepaths_w_shortened_urls: dict[Path, list[tuple[str, str]]] = {}

    # Shorten each URL and add both the original and shortened URLs to the spreadsheet
    for i, original_url in enumerate(all_urls):
        logger.info(f'Shortening url {i + 1} of {len(all_urls)}')
        shortened_url = shorten_url(original_url, yourls)
        if shortened_url:
            for filepath, urls in file_urls.items():
                if original_url in urls:
                    filepaths_w_shortened_urls.setdefault(filepath, []).append((original_url, shortened_url))
        time.sleep(1) # pause to avoid overburdening API

    # sort tuples in descending order by original_url
    for filepath, url_pairs in filepaths_w_shortened_urls.items():
        filepaths_w_shortened_urls[filepath] = sorted(
            url_pairs,
            key=lambda pair: len(pair[0]),  # pair[0] is the original URL
            reverse=True  # Descending order
        )

    # make replacements
    for filepath, url_tuples in filepaths_w_shortened_urls.items():
        update_file_content(filepath, url_tuples)

    return filepaths_w_shortened_urls
