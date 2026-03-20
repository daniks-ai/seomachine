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

# Model to use
MODEL = "fal-ai/nano-banana-2"


def _detect_visual_theme(title: str, topic: str) -> dict:
    """Detect the best visual theme based on article title and topic keywords.

    Themes are ordered from most specific to least specific keywords.
    Each theme uses a deliberately different subject, lighting, and color palette
    to ensure visual diversity across the blog grid.
    """
    text = f"{title} {topic}".lower()

    # Ordered: specific keywords first, broad catch-all keywords last.
    # Each theme deliberately varies: subject matter, dominant color temperature,
    # lighting style, and camera angle to avoid visual similarity.
    themes = [
        {
            # Specific: ACoS/TACoS metrics comparison
            "keywords": ["acos vs tacos", "tacos vs acos"],
            "scene": "two transparent glass measuring cups side by side on a bright white lab bench — "
                     "one filled with warm amber liquid, the other with deep emerald green liquid, "
                     "both casting colorful shadows, clean scientific lighting from above",
            "mood": "measurement, clarity, analytical comparison",
            "style": "scientific still life, bright clinical lighting, clean white background, glass reflections",
            "palette": "warm amber (#e09f3e) and emerald green (#2d6a4f) with clean white (#ffffff)",
        },
        {
            # Specific: "vs" / "versus" tool comparison articles
            "keywords": ["vs ", "versus"],
            "scene": "a polished brass balance scale on a white marble surface, the left pan holding a warm orange glass orb "
                     "and the right pan holding a cool blue glass orb, balanced perfectly, soft diffused studio light from above",
            "mood": "balanced evaluation, thoughtful choice",
            "style": "elegant product photography, bright key lighting, shallow depth of field",
            "palette": "warm orange (#e76f51) and cool blue (#457b9d) with cream marble (#f8f9fa) and brass gold (#c9a227)",
        },
        {
            # Specific: "best" / "top" listicle articles
            "keywords": ["best ", "top ", " tools"],
            "scene": "a top-down view of a clean white pegboard with seven different colorful miniature tools "
                     "hung in a neat row — each a different bright color, evenly spaced, "
                     "flat studio lighting, organized and satisfying composition",
            "mood": "curated selection, clarity, organized choice",
            "style": "overhead flat-lay, bright even lighting, playful product arrangement, clean white background",
            "palette": "rainbow accents on white (#ffffff) — red (#e63946), orange (#f4a261), yellow (#e9c46a), "
                     "green (#2a9d8f), blue (#264653), purple (#7209b7)",
        },
        {
            # Specific: China / global marketplace
            "keywords": ["china", "chinese", "europe", "global", "marketplace"],
            "scene": "a beautifully styled world map printed on aged parchment paper, with small colored pins marking key locations, "
                     "warm desk lamp lighting, a compass sitting at the corner, slightly overhead angle",
            "mood": "global reach, exploration, opportunity",
            "style": "vintage travel photography, warm tungsten light, textured surfaces",
            "palette": "parchment tan (#d4a373) with ocean teal (#457b9d) and burgundy (#780000)",
        },
        {
            # Specific: automation / AI
            "keywords": ["automation", "automate", "autopilot", "ai manage"],
            "scene": "a robotic hand and a human hand about to touch fingertips across a soft gradient background, "
                     "warm golden light between the fingers, clean futuristic but warm composition",
            "mood": "collaboration, intelligent automation, human plus machine",
            "style": "cinematic portrait lighting, warm-cool contrast, shallow depth of field",
            "palette": "warm gold (#f0a500) with slate blue (#475569) and soft white (#f8fafc)",
        },
        {
            # Specific: beginner / getting started (before financial to avoid "profitable" false match)
            "keywords": ["beginner", "getting started", "first step"],
            "scene": "a bright overhead flat-lay of a clean desk with a compass, a small paper airplane, colorful sticky notes, "
                     "a sharpened pencil, and a potted succulent, morning sunlight casting soft shadows on light wood",
            "mood": "fresh start, confidence, readiness",
            "style": "lifestyle flat-lay, bright cheerful daylight, overhead angle",
            "palette": "light wood (#deb887), bright teal (#20b2aa), sunshine yellow (#ffd700), soft white (#fafafa)",
        },
        {
            # Specific: bidding / auction
            "keywords": ["bid", "bidding", "auction"],
            "scene": "a stylized wooden gavel mid-strike on a polished dark wood surface, "
                     "a single warm spotlight creating dramatic long shadows, minimalist composition",
            "mood": "action, decisiveness, competition",
            "style": "dramatic product photography, single spotlight, deep shadows, cinematic",
            "palette": "rich mahogany (#6b0f1a) with warm gold (#edb230) and charcoal (#2b2d42)",
        },
        {
            # Specific: ACoS / cost / budget (financial) — avoid broad words like "profit"
            "keywords": ["acos", "tacos", "roas", "cost", "budget", "spend", "margin", "lower"],
            "scene": "a neat row of stacked gold coins decreasing in height from left to right like a descending bar chart "
                     "on a clean white marble surface, a small green succulent in the corner, bright airy window light",
            "mood": "smart savings, financial clarity, efficiency",
            "style": "flat-lay photography, bright and airy, overhead shot, minimal styling",
            "palette": "gold (#d4a853) with white marble (#f8f9fa) and forest green (#2d6a4f)",
        },
        {
            # Specific: keyword / targeting
            "keywords": ["keyword", "targeting", "search term", "match type", "negative keyword"],
            "scene": "a single red dart stuck perfectly in the bullseye center of a dartboard, "
                     "shot from a slight angle with the background softly blurred into warm wood tones",
            "mood": "precision, focus, hitting the mark",
            "style": "sports photography, shallow depth of field, warm ambient light",
            "palette": "deep red (#c1121f) with cream (#ffe8d6) and dark walnut (#5c4033)",
        },
        {
            # Specific: reviews / ratings / reputation
            "keywords": ["review", "rating", "feedback", "reputation"],
            "scene": "five elegant origami stars arranged in a row on a clean white surface, the first four in gold paper "
                     "and the fifth partially folded, soft diffused window light, minimal composition",
            "mood": "trust, quality, social proof",
            "style": "still life photography, soft diffused light, minimal, clean background",
            "palette": "warm gold (#dda15e) with soft white (#fafafa) and light gray (#e9ecef)",
        },
        {
            # Specific: campaign structure / account organization
            "keywords": ["campaign", "structure", "organize", "account"],
            "scene": "a neatly organized set of colorful wooden building blocks forming a tiered pyramid on a light birch desk, "
                     "each tier a different pastel color, soft directional light from the right, clean white background",
            "mood": "order, hierarchy, solid foundation",
            "style": "product photography, bright clean background, directional light, tactile materials",
            "palette": "pastel blue (#a8dadc), pastel green (#a7c4a0), pastel peach (#ffcdb2) with light wood (#deb887)",
        },
        {
            # Specific: analytics / data / performance
            "keywords": ["data", "analytics", "report", "metric", "performance", "analysis"],
            "scene": "a close-up of a crystal prism refracting a beam of white light into a vivid rainbow spectrum, "
                     "set against a clean gradient background, the light beams sharply defined",
            "mood": "insight, breaking down complexity, clarity",
            "style": "scientific photography, clean composition, precise lighting, modern",
            "palette": "prismatic spectrum on clean white (#ffffff) fading to soft lavender (#e2d1f9)",
        },
        {
            # Broad: comparison / alternative (non-"vs" comparisons)
            "keywords": ["comparison", "alternative", "compared", "switch"],
            "scene": "two distinct paths diverging in a bright sunlit garden — one path is red brick, the other pale stone, "
                     "with green hedges on both sides and warm golden hour sunlight",
            "mood": "choice, divergent options, clarity",
            "style": "landscape photography, golden hour, warm and inviting, eye-level perspective",
            "palette": "terracotta (#c4633d) with pale stone (#e8e0d5) and garden green (#588157)",
        },
        {
            # Broad: strategy / guide / framework / plan (catch-all for strategic content)
            "keywords": ["strategy", "plan", "framework", "playbook", "roadmap", "guide"],
            "scene": "an overhead view of an architect's desk with a clean blueprint, a brass compass, a wooden ruler, "
                     "and a white ceramic cup of coffee, morning sunlight streaming in from the left",
            "mood": "expertise, planning, craftsmanship",
            "style": "lifestyle flat-lay, morning light, warm editorial, overhead angle",
            "palette": "blueprint blue (#1d3557) with warm white (#f1faee) and copper (#b08968)",
        },
    ]

    for theme in themes:
        if any(kw in text for kw in theme["keywords"]):
            return theme

    # Default theme — warm, bright, neutral
    return {
        "keywords": [],
        "scene": "a single lit beeswax candle with a warm flame on a clean white ceramic dish, "
                 "next to a small potted green plant, soft morning window light, airy and minimal composition",
        "mood": "professional, focused, calm clarity",
        "style": "lifestyle still life, bright and airy, natural light, minimal",
        "palette": "warm honey (#e09f3e) with soft white (#fefefe) and sage green (#a3b18a)",
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
            "resolution": "2K",
            "aspect_ratio": "16:9",
            "num_images": 1,
            "output_format": "jpeg",
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
