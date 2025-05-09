import logging
from yourls import YOURLSClientBase, YOURLSAPIMixin


logger = logging.getLogger(__name__)


class YOURLSDeleteMixin(object):
    def delete(self, short):
        data = dict(action='delete', shorturl=short)
        response = self._api_request(params=data)
        response_message = response.get('message')
        if 'success' in response_message:
            logger.info(f"Deleted: {short}")
            return(True)
        else:
            logger.info(f"Failed to delete: {short}. Reason: {response.get('message')}")
            return(False)


class YOURLSClient(YOURLSDeleteMixin, YOURLSAPIMixin, YOURLSClientBase):
    """YOURLS client with API delete support."""
    pass


def delete_urls(short_urls: list[str], yourls_url, yourls_key):
    results = []
    yourls = YOURLSClient(yourls_url, yourls_key)
    
    for short_url in short_urls:
        result = yourls.delete(short_url)
        results.append(result)
    
    return results
