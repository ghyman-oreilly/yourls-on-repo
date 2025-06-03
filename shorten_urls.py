import logging
from pathlib import Path
import requests
import sys
import time
from yourls import YOURLSClient


logger = logging.getLogger(__name__)


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
        # requests can't parse JSON because service is unavailable
        # hacky error handling, but I find no better options for checking YOURLS server availability
        # (no built-in methods; server forbids GET and HEAD requests)
        if "Expecting value: line 1 column 1" in str(exc):
            logger.error(f"RequestException: {exc}.\nPlease check your VPN connection. Exiting.")
            sys.exit(1)
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
