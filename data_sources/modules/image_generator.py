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


def _load_env_local():
    """Load FAL_KEY from .env_local if not already set."""
    if os.environ.get("FAL_KEY"):
        return
    env_local = os.path.join(os.path.dirname(__file__), "..", "config", ".env_local")
    if os.path.exists(env_local):
        with open(env_local) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip("'").strip('"')
                    os.environ.setdefault(key.strip(), val)


_load_env_local()

# Default output directory (relative to repo root)
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "daniks-ai-ads", "src", "assets", "blog"
)

# Image dimensions for blog og:image
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 630

# Model to use
MODEL = "fal-ai/flux/dev"


def _detect_visual_theme(title: str, topic: str) -> dict:
    """Detect the best visual theme based on article title and topic keywords."""
    text = f"{title} {topic}".lower()

    themes = [
        {
            "keywords": ["vs ", "versus", "comparison", "alternative", "compared"],
            "scene": "a clean split-screen composition — left side shows a polished red chess piece, right side a white chess piece, "
                     "separated by a thin vertical light beam, soft gradient background fading from warm to cool",
            "mood": "tension, choice, contrast",
            "style": "minimal product photography, soft studio lighting, matte surfaces",
            "palette": "warm coral (#e07a5f) against cool slate (#3d405b) with cream (#f4f1de) divider",
        },
        {
            "keywords": ["automation", "automate", "autopilot", "ai manage", "machine learning"],
            "scene": "a close-up of a perfectly balanced mechanical clockwork mechanism with brass gears interlocking, "
                     "one gear replaced by a translucent crystal gear suggesting AI, soft natural light from the side",
            "mood": "precision, intelligence, effortless control",
            "style": "macro photography, natural light, shallow depth of field, warm tones",
            "palette": "warm brass (#c9a227) with cream (#fefae0) and deep brown (#3a2d1e) accents",
        },
        {
            "keywords": ["acos", "roas", "cost", "budget", "spend", "profit", "margin", "roi"],
            "scene": "a top-down flat-lay of neatly arranged coins and bills forming an upward arrow pattern on a marble surface, "
                     "with a small green plant growing at the arrow tip, bright airy lighting",
            "mood": "financial growth, clarity, smart money",
            "style": "flat-lay photography, bright and airy, overhead shot, clean styling",
            "palette": "forest green (#2d6a4f) with white marble (#f8f9fa) and gold (#d4a853)",
        },
        {
            "keywords": ["keyword", "targeting", "search term", "match type", "negative keyword"],
            "scene": "a dartboard photographed from a slight angle with one dart hitting the exact center bullseye, "
                     "the background softly blurred showing a warm wooden wall, natural warm light",
            "mood": "precision, focus, hitting the mark",
            "style": "sports photography, shallow depth of field, warm ambient light",
            "palette": "deep red (#c1121f) with cream (#ffe8d6) and dark walnut (#5c4033)",
        },
        {
            "keywords": ["strategy", "plan", "framework", "playbook", "roadmap", "guide"],
            "scene": "an overhead view of an architect's desk with a clean blueprint, a compass, a ruler, and a cup of coffee, "
                     "morning sunlight streaming in from the left casting soft shadows",
            "mood": "expertise, planning, craftsmanship",
            "style": "lifestyle flat-lay, morning light, warm editorial, overhead angle",
            "palette": "blueprint blue (#1d3557) with warm white (#f1faee) and copper (#b08968)",
        },
        {
            "keywords": ["bid", "bidding", "auction"],
            "scene": "a stylized wooden gavel mid-strike with motion blur at the tip, sitting on a polished dark wood surface, "
                     "a single spotlight creating dramatic shadows, minimalist composition",
            "mood": "action, decisiveness, competition",
            "style": "dramatic product photography, single spotlight, deep shadows, cinematic",
            "palette": "rich mahogany (#6b0f1a) with warm gold (#edb230) and charcoal (#2b2d42)",
        },
        {
            "keywords": ["review", "rating", "feedback", "reputation"],
            "scene": "five elegant origami stars arranged in a row on a clean white surface, the first four in gold paper "
                     "and the fifth partially folded, soft diffused window light, minimal composition",
            "mood": "trust, quality, social proof",
            "style": "still life photography, soft diffused light, minimal, clean background",
            "palette": "warm gold (#dda15e) with soft white (#fafafa) and light gray (#e9ecef)",
        },
        {
            "keywords": ["data", "analytics", "report", "metric", "performance", "analysis"],
            "scene": "a close-up of a crystal prism refracting a beam of white light into a vivid rainbow spectrum, "
                     "set against a clean gradient background, the light beams sharply defined",
            "mood": "insight, breaking down complexity, clarity",
            "style": "scientific photography, clean composition, precise lighting, modern",
            "palette": "prismatic spectrum on clean white (#ffffff) fading to soft lavender (#e2d1f9)",
        },
        {
            "keywords": ["launch", "new", "start", "beginner", "getting started", "first"],
            "scene": "a single paper airplane in mid-flight against a clear bright sky with a few soft clouds, "
                     "shot from below looking up, the airplane casting a small shadow, bright and optimistic",
            "mood": "momentum, fresh start, energy",
            "style": "outdoor photography, bright daylight, upward angle, optimistic composition",
            "palette": "sky blue (#a2d2ff) with white (#ffffff) and sunshine yellow (#ffdd00)",
        },
        {
            "keywords": ["china", "chinese", "seller", "marketplace", "europe", "global"],
            "scene": "a beautifully styled world map printed on aged parchment paper, with small colored pins marking key locations, "
                     "warm desk lamp lighting, a compass sitting at the corner, slightly overhead angle",
            "mood": "global reach, exploration, opportunity",
            "style": "vintage travel photography, warm tungsten light, textured surfaces",
            "palette": "parchment tan (#d4a373) with ocean teal (#457b9d) and burgundy (#780000)",
        },
        {
            "keywords": ["campaign", "structure", "organize", "account"],
            "scene": "a neatly organized set of wooden building blocks forming a tiered pyramid structure on a clean desk, "
                     "each tier a different natural wood shade, soft directional light from the right",
            "mood": "order, hierarchy, solid foundation",
            "style": "product photography, clean background, directional light, tactile materials",
            "palette": "natural wood (#c4a77d) with soft sage (#a7c4a0) and warm gray (#8d99ae)",
        },
    ]

    for theme in themes:
        if any(kw in text for kw in theme["keywords"]):
            return theme

    # Default theme
    return {
        "keywords": [],
        "scene": "a single lit candle flame reflected in a perfectly still pool of water on a polished concrete surface, "
                 "creating a mirror image, soft ambient light, meditative and focused composition",
        "mood": "professional, focused, authoritative",
        "style": "fine art photography, minimal, reflective surfaces, natural light",
        "palette": "warm amber (#e09f3e) with cool charcoal (#335c67) and soft cream (#fff3b0)",
    }


def build_prompt(article_title: str, article_topic: str = "") -> str:
    """Build a rich, topic-specific image generation prompt."""
    theme = _detect_visual_theme(article_title, article_topic)
    topic_hint = article_topic if article_topic else article_title

    return (
        f"{theme['scene']}. "
        f"The overall mood is {theme['mood']}. "
        f"Style: {theme['style']}. "
        f"Color palette: {theme['palette']}. "
        "Ultra high quality, 8K render, photorealistic. "
        "Absolutely no text, no words, no letters, no numbers, no UI elements, no watermarks. "
        "Horizontal 1200x630 composition with strong visual center and breathing room on sides."
    )


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
