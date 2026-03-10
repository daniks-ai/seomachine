"""
Generate blog featured images using fal.ai API.

Usage:
    python data_sources/modules/image_generator.py "Article title" --slug "article-slug" --output "../daniks-ai-ads/src/assets/blog/"

Requires:
    pip install fal-client
    export FAL_KEY='your_fal_api_key'
"""

import os
import sys
import argparse
import requests
import json

try:
    import fal_client
except ImportError:
    print("Error: fal-client not installed. Run: pip install fal-client")
    sys.exit(1)


# Default output directory (relative to repo root)
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "daniks-ai-ads", "src", "assets", "blog"
)

# Image dimensions for blog og:image
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 630

# Model to use
MODEL = "fal-ai/flux/dev"


def build_prompt(article_title: str, article_topic: str = "") -> str:
    """Build an image generation prompt from the article title and topic."""
    base = (
        "Professional, modern blog featured image for an Amazon seller resource. "
        "Clean, minimal design with a dark blue and teal color palette. "
        "Abstract digital/tech aesthetic with subtle data visualization elements. "
        "No text, no words, no letters, no watermarks. "
        "High quality, editorial style, suitable for a SaaS company blog. "
    )
    topic_hint = article_topic if article_topic else article_title
    return f"{base}Topic: {topic_hint}"


def generate_image(prompt: str) -> str:
    """Generate an image using fal.ai and return the image URL."""
    if not os.environ.get("FAL_KEY"):
        raise EnvironmentError("FAL_KEY environment variable not set. Get your key at https://fal.ai/dashboard/keys")

    result = fal_client.subscribe(
        MODEL,
        arguments={
            "prompt": prompt,
            "image_size": {
                "width": IMAGE_WIDTH,
                "height": IMAGE_HEIGHT,
            },
            "num_images": 1,
        },
    )

    return result["images"][0]["url"]


def download_image(url: str, output_path: str) -> str:
    """Download image from URL to local path."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def generate_blog_image(article_title: str, slug: str, output_dir: str = None, topic: str = "") -> str:
    """
    Full pipeline: generate image for a blog post and save it.

    Args:
        article_title: The article's H1 title
        slug: URL slug for the article (used as filename)
        output_dir: Directory to save the image
        topic: Optional topic hint for better image generation

    Returns:
        Path to the saved image file
    """
    if output_dir is None:
        output_dir = os.path.abspath(DEFAULT_OUTPUT_DIR)

    prompt = build_prompt(article_title, topic)
    print(f"Generating image for: {article_title}")
    print(f"Model: {MODEL}")
    print(f"Prompt: {prompt[:100]}...")

    image_url = generate_image(prompt)
    print(f"Image generated: {image_url}")

    filename = f"{slug}.jpg"
    output_path = os.path.join(output_dir, filename)
    download_image(image_url, output_path)
    print(f"Image saved to: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate blog featured images using fal.ai")
    parser.add_argument("title", help="Article title for image generation")
    parser.add_argument("--slug", required=True, help="URL slug (used as filename)")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--topic", default="", help="Optional topic hint for better results")
    parser.add_argument("--prompt-only", action="store_true", help="Only print the prompt, don't generate")

    args = parser.parse_args()

    if args.prompt_only:
        print(build_prompt(args.title, args.topic))
        return

    output_dir = args.output if args.output else os.path.abspath(DEFAULT_OUTPUT_DIR)
    path = generate_blog_image(args.title, args.slug, output_dir, args.topic)
    print(f"\nDone! Image at: {path}")


if __name__ == "__main__":
    main()
