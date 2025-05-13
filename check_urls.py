import requests
import time


def check_urls(urls: set):
    """
    Request URLS in a set to check for error responses.  
    """
    # List to store bad URLs
    bad_urls = []

    # Request URLs and obtain error codes when encountered
    for url in urls:
        
        try:
            request = requests.get(url)
            response = request.status_code # e.g., 200, 404
        except:
            response = None
        
        if response == None:
            # request failed
            bad_urls.append("Request failed: " + url)

        elif response != requests.codes.ok:
            # response is among codes categorized as error codes (not in built-in requests.codes.ok)
            bad_urls.append(str(response) + " error: " + url)

        time.sleep(1)

    return bad_urls
