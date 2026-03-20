"""
Google Indexing API - Request URL indexing via Google's Indexing API.

Uses the same service account credentials as Google Search Console.
The service account must be added as an owner in Google Search Console
for the target site.

Usage:
    python data_sources/modules/google_indexing.py "https://daniks.ai/blog/my-article"
"""

import os
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build


def request_indexing(url: str, credentials_path: str = None) -> dict:
    """
    Request Google to index a URL using the Indexing API.

    Args:
        url: The URL to request indexing for
        credentials_path: Path to service account JSON credentials

    Returns:
        dict with API response or error details
    """
    credentials_path = credentials_path or os.getenv('GSC_CREDENTIALS_PATH')

    if not credentials_path or not os.path.exists(credentials_path):
        return {
            "success": False,
            "error": f"Credentials file not found: {credentials_path}",
            "hint": "Set GSC_CREDENTIALS_PATH env var or pass credentials_path"
        }

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/indexing']
        )

        service = build('indexing', 'v3', credentials=credentials)

        body = {
            'url': url,
            'type': 'URL_UPDATED'
        }

        response = service.urlNotifications().publish(body=body).execute()

        return {
            "success": True,
            "url": url,
            "notifyTime": response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('notifyTime'),
            "response": response
        }

    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python google_indexing.py <url>")
        print("Example: python google_indexing.py https://daniks.ai/blog/my-article")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Requesting indexing for: {url}")

    result = request_indexing(url)
    print(json.dumps(result, indent=2))

    sys.exit(0 if result["success"] else 1)
