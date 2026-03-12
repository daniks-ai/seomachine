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
            "scene": "split-screen composition, two distinct glowing objects facing each other across a divide, "
                     "one side cool blue, the other warm orange, dramatic lighting from the center gap",
            "mood": "tension, choice, contrast",
        },
        {
            "keywords": ["automation", "automate", "autopilot", "ai manage", "machine learning"],
            "scene": "a sleek robotic arm or mechanical hand delicately adjusting floating holographic dials and sliders, "
                     "streams of glowing data particles flowing through the scene, dark environment with teal and amber accents",
            "mood": "precision, intelligence, futuristic control",
        },
        {
            "keywords": ["acos", "roas", "cost", "budget", "spend", "profit", "margin", "roi"],
            "scene": "an abstract 3D landscape where geometric mountains and valleys represent rising and falling metrics, "
                     "a glowing golden path winding through to a bright peak, dark navy environment",
            "mood": "financial clarity, optimization, progress",
        },
        {
            "keywords": ["keyword", "targeting", "search term", "match type", "negative keyword"],
            "scene": "a vast dark space filled with hundreds of softly glowing orbs of different sizes, "
                     "a few orbs highlighted with bright rings and connected by luminous threads forming a constellation, "
                     "shallow depth of field",
            "mood": "discovery, precision, focus among noise",
        },
        {
            "keywords": ["strategy", "plan", "framework", "playbook", "roadmap", "guide"],
            "scene": "an intricate glowing blueprint or architectural wireframe floating in dark space, "
                     "with layers peeling apart to show depth, teal and white light tracing the edges, "
                     "isometric perspective",
            "mood": "structure, expertise, master plan",
        },
        {
            "keywords": ["bid", "bidding", "auction"],
            "scene": "an abstract auction scene with floating price tags and bid paddles rendered as sleek 3D objects, "
                     "ascending staircase of light representing bid increments, dramatic spotlight from above",
            "mood": "competition, timing, strategic action",
        },
        {
            "keywords": ["review", "rating", "feedback", "reputation"],
            "scene": "luminous star shapes at various sizes scattered across a dark gradient, "
                     "some stars fully bright, others partially lit, creating a constellation pattern, "
                     "warm gold and cool navy palette",
            "mood": "trust, social proof, quality",
        },
        {
            "keywords": ["data", "analytics", "report", "metric", "performance", "analysis"],
            "scene": "a beautiful 3D data visualization floating in dark space — glowing bar charts morphing into "
                     "flowing wave forms, particle streams connecting data points, "
                     "holographic dashboard aesthetic with teal, purple, and white accents",
            "mood": "insight, clarity, intelligence",
        },
        {
            "keywords": ["launch", "new", "start", "beginner", "getting started", "first"],
            "scene": "a single bright rocket or arrow made of light, trailing luminous particles as it ascends "
                     "through layers of cloud-like gradients, transitioning from dark base to bright peak",
            "mood": "momentum, beginning, energy",
        },
        {
            "keywords": ["china", "chinese", "seller", "marketplace", "europe", "global"],
            "scene": "an abstract globe or world map rendered as a network of glowing nodes and connections, "
                     "certain regions pulsing brighter, trade route lines arcing between continents, "
                     "dark background with warm and cool accent colors",
            "mood": "global scale, interconnection, market dynamics",
        },
        {
            "keywords": ["campaign", "structure", "organize", "account"],
            "scene": "an elegant tree diagram or organizational chart made of glowing nodes and branches, "
                     "each level a different color intensity, floating in dark space with subtle grid lines behind",
            "mood": "order, hierarchy, clean architecture",
        },
    ]

    for theme in themes:
        if any(kw in text for kw in theme["keywords"]):
            return theme

    # Default theme
    return {
        "keywords": [],
        "scene": "an abstract composition of flowing light ribbons and geometric shapes in a dark environment, "
                 "with depth layers creating a sense of dimension, teal and amber accent lighting",
        "mood": "professional, modern, authoritative",
    }


def build_prompt(article_title: str, article_topic: str = "") -> str:
    """Build a rich, topic-specific image generation prompt."""
    theme = _detect_visual_theme(article_title, article_topic)
    topic_hint = article_topic if article_topic else article_title

    return (
        f"Cinematic wide-angle photograph, {theme['scene']}. "
        f"The overall mood is {theme['mood']}. "
        f"Inspired by the concept: {topic_hint}. "
        "Style: editorial photography meets digital art, shallow depth of field, "
        "volumetric lighting, rich shadows, subtle lens flare. "
        "Color palette: deep navy (#0f172a) base with teal (#0d9488) and warm amber (#f59e0b) accents. "
        "Ultra high quality, 8K render, photorealistic materials with abstract subject matter. "
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
