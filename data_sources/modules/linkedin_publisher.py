"""
LinkedIn Publisher — publishes a post (text + image + link) to a LinkedIn
company page using the LinkedIn Posts API (Versioned, REST namespace).

One-time setup:
    1. Create a LinkedIn app at https://www.linkedin.com/developers/apps
    2. Associate it with the company page (Settings tab)
    3. Request products: "Share on LinkedIn" and "Community Management API"
    4. Get a long-lived access token with scopes:
         w_organization_social, r_organization_social
       (Tokens last 60 days; refresh from the developer portal.)
    5. Find the numeric organization ID from your company page URL or via
         GET https://api.linkedin.com/v2/organizationAcls?q=roleAssignee

Env vars (loaded from data_sources/config/.env):
    LINKEDIN_ACCESS_TOKEN    - OAuth2 access token
    LINKEDIN_ORGANIZATION_ID - Numeric organization ID (e.g. 12345678)
    LINKEDIN_API_VERSION     - Versioned API header (default: 202401)

Usage:
    python data_sources/modules/linkedin_publisher.py \
        --text-file published/my-article-linkedin.txt \
        --image /path/to/image.jpg \
        --link https://daniks.ai/blog/my-article \
        --title "My Article Title"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import requests


LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"
# LinkedIn versions the REST API by month (YYYYMM) and keeps each version active
# for ~12 months before sunset; a stale version returns HTTP 426 NONEXISTENT_VERSION.
# Keep this within the trailing year and bump it when LinkedIn retires it. Override
# per-deployment via LINKEDIN_API_VERSION in data_sources/config/.env.
DEFAULT_API_VERSION = "202606"


def _import_auth():
    """Import the sibling linkedin_auth module regardless of how this file is run.

    Returns the module, or None if it can't be imported (so publishing still works
    with only a static LINKEDIN_ACCESS_TOKEN configured).
    """
    import importlib

    mod_dir = str(Path(__file__).resolve().parent)
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    try:
        return importlib.import_module("linkedin_auth")
    except Exception:
        return None


def resolve_access_token() -> Optional[str]:
    """Prefer the auto-refreshing managed token store; fall back to the static
    LINKEDIN_ACCESS_TOKEN env var for backward compatibility.

    Propagates linkedin_auth.LinkedInReauthRequired so an expired store fails
    loudly instead of silently posting with a dead token.
    """
    linkedin_auth = _import_auth()
    if linkedin_auth is not None:
        try:
            managed = linkedin_auth.get_managed_token()
        except linkedin_auth.LinkedInReauthRequired:
            raise
        except Exception:
            managed = None
        if managed:
            return managed
    return os.getenv("LINKEDIN_ACCESS_TOKEN")

# Per LinkedIn Posts API "Little Text" format, these characters must be
# backslash-escaped to appear literally. We deliberately omit '#' and '@' so
# hashtag and member mention syntax still works naturally in the post body.
_ESCAPE_CHARS = set("()[]{}<>|~_*\\")


def escape_commentary(text: str) -> str:
    """Backslash-escape special characters in LinkedIn post commentary."""
    return "".join("\\" + c if c in _ESCAPE_CHARS else c for c in text)


class LinkedInPublisher:
    def __init__(
        self,
        access_token: Optional[str] = None,
        organization_id: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.access_token = access_token or resolve_access_token()
        self.organization_id = organization_id or os.getenv("LINKEDIN_ORGANIZATION_ID")
        self.api_version = api_version or os.getenv("LINKEDIN_API_VERSION", DEFAULT_API_VERSION)

        if not self.access_token:
            raise ValueError(
                "No LinkedIn access token available. Run "
                "`python data_sources/modules/linkedin_auth.py login` once, or set "
                "LINKEDIN_ACCESS_TOKEN in data_sources/config/.env"
            )
        if not self.organization_id:
            raise ValueError("LINKEDIN_ORGANIZATION_ID must be set")

        self.author_urn = f"urn:li:organization:{self.organization_id}"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def upload_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        init_url = f"{LINKEDIN_REST_BASE}/images?action=initializeUpload"
        init_body = {"initializeUploadRequest": {"owner": self.author_urn}}
        r = requests.post(
            init_url,
            headers={**self.headers, "Content-Type": "application/json"},
            json=init_body,
            timeout=30,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Image initializeUpload failed ({r.status_code}): {r.text}")
        value = r.json().get("value", {})
        upload_url = value.get("uploadUrl")
        image_urn = value.get("image")
        if not upload_url or not image_urn:
            raise RuntimeError(f"Unexpected initializeUpload response: {r.text}")

        with open(path, "rb") as f:
            payload = f.read()
        # Binary upload uses only the bearer token — no LinkedIn-Version header.
        ur = requests.put(
            upload_url,
            data=payload,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=120,
        )
        if ur.status_code >= 400:
            raise RuntimeError(f"Image binary upload failed ({ur.status_code}): {ur.text}")

        return image_urn

    def create_post(
        self,
        commentary: str,
        image_urn: Optional[str] = None,
        image_alt: str = "",
        article_url: Optional[str] = None,
        article_title: Optional[str] = None,
    ) -> Dict:
        body = {
            "author": self.author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        # An image attachment makes the post visually richer and gets ~1.7x
        # engagement. The article URL is included inline in the commentary so
        # readers still have a click target. If no image is available, fall
        # back to a link preview so the post still has a thumbnail.
        if image_urn:
            body["content"] = {
                "media": {
                    "id": image_urn,
                    "altText": (image_alt or article_title or "")[:200],
                }
            }
        elif article_url:
            body["content"] = {
                "article": {
                    "source": article_url,
                    "title": (article_title or "")[:400],
                }
            }

        r = requests.post(
            f"{LINKEDIN_REST_BASE}/posts",
            headers={**self.headers, "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Post create failed ({r.status_code}): {r.text}")

        post_urn = r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id")
        return {
            "success": True,
            "post_urn": post_urn,
            "post_url": (
                f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else None
            ),
        }


def publish(
    commentary: str,
    image_path: Optional[str] = None,
    article_url: Optional[str] = None,
    article_title: Optional[str] = None,
) -> Dict:
    pub = LinkedInPublisher()
    image_urn = pub.upload_image(image_path) if image_path else None
    return pub.create_post(
        commentary=escape_commentary(commentary),
        image_urn=image_urn,
        image_alt=article_title or "",
        article_url=article_url,
        article_title=article_title,
    )


def _main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv("data_sources/config/.env")
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Publish a post to a LinkedIn company page")
    parser.add_argument("--text", help="Post commentary text")
    parser.add_argument("--text-file", help="Path to a file containing post commentary")
    parser.add_argument("--image", help="Path to featured image (optional but recommended)")
    parser.add_argument("--link", help="Article URL — included inline in copy and used as link preview fallback")
    parser.add_argument("--title", help="Article title — used for image alt text and link preview title")
    args = parser.parse_args()

    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read().strip()
    if not text:
        print("Error: --text or --text-file is required", file=sys.stderr)
        return 2

    try:
        result = publish(text, args.image, args.link, args.title)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(_main())
