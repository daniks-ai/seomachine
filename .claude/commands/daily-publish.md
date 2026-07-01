# Daily Auto-Publish Pipeline

Fully automated pipeline: pick a topic, research, write, generate image, publish to website, commit & push.

## Usage
This command is designed to run unattended via `claude -p`. Do NOT ask the user any questions. Make all decisions autonomously.

## Full Pipeline

Execute these steps in order. If any step fails critically, save progress and stop.

### Step 1: Pick a Topic

Choose the next article topic automatically using this priority:

1. **Check `topics/` folder** for any pre-planned topics (files with topic ideas)
2. **Check `context/target-keywords.md`** for high-priority keywords that don't have content yet
3. **Check `context/competitor-analysis.md`** for content gaps and opportunities
4. **Check existing blog posts** in `context/internal-links-map.md` to avoid duplicates

Select a topic that:
- Has NOT been written about already (check `drafts/`, `published/`, and the internal links map)
- Targets a keyword cluster from target-keywords.md
- Has commercial or informational intent relevant to Amazon sellers
- Complements existing content (builds out topic clusters)

Save the chosen topic and reasoning to `topics/auto-selected-[YYYY-MM-DD].md`.

### Step 2: Research Context

Read these context files to inform the article:
- `context/brand-voice.md` - Voice and tone
- `context/features.md` - Product details for natural mentions
- `context/seo-guidelines.md` - SEO requirements
- `context/style-guide.md` - Formatting standards
- `context/writing-examples.md` - Style reference
- `context/target-keywords.md` - Keywords to target
- `context/internal-links-map.md` - Internal links to include
- `context/competitor-analysis.md` - Competitive context

### Step 2b: SERP Research with DataForSEO

Run SERP analysis for the chosen primary keyword to get real search data:

```bash
python3 research_serp_analysis.py "primary keyword phrase"
```

This will:
1. Fetch top 10 organic results from DataForSEO (search volume, competition, CPC)
2. Analyze content patterns (dominant content type, word counts, freshness signals)
3. Detect SERP features (featured snippets, People Also Ask, etc.)
4. Assess competitive difficulty
5. Generate a content brief saved to `research/serp-analysis-[keyword].md`

**Use the SERP analysis results to inform your article:**
- Match or exceed the recommended word count
- Follow the dominant content type (listicle, how-to, guide, etc.)
- Target identified SERP features (add FAQ section if PAA is present, etc.)
- Include the year in title if freshness is important
- Cover topics that top-ranking competitors all cover
- Address content gaps the analysis identifies

If DataForSEO fails (credentials missing, API error), continue with the pipeline using context files only — do NOT stop.

### Step 3: Write the Article

Write a complete, SEO-optimized article following ALL requirements from the `/write` command:

- 2000-3000 words
- Proper H1/H2/H3 structure
- Primary keyword in H1, first 100 words, 2-3 H2s, conclusion
- 1-2% keyword density
- Compelling hook (NOT a generic opening)
- 2-3 mini-stories with specific names and scenarios
- 2-3 contextual CTAs distributed throughout
- 3-5 internal links (from internal-links-map.md)
- 2-3 external authority links
- Daniks.AI brand voice throughout
- Meta title (50-60 chars), meta description (150-160 chars), URL slug

Save the article to: `drafts/[slug]-[YYYY-MM-DD].md`

### Step 4: Scrub AI Watermarks

Run the content scrubber on the draft to remove AI signatures:
```bash
python data_sources/modules/content_scrubber.py drafts/[article-file].md
```

If the scrubber script is not available, manually ensure:
- No invisible Unicode characters
- Em-dashes replaced with appropriate punctuation where overused
- No telltale AI phrases ("delve", "landscape", "it's important to note", "in today's")

### Step 5: Generate Featured Image

Generate a blog featured image using fal.ai:
```bash
python data_sources/modules/image_generator.py "[Article Title]" \
  --slug "[article-slug]" \
  --output "/Users/ync/poryadok/sources/daniks-ai-ads/src/assets/blog/" \
  --topic "[brief topic description for image prompt]"
```

The image will be saved to `daniks-ai-ads/src/assets/blog/[slug].jpg`.

If image generation fails (no FAL_KEY, API error), continue with the pipeline but note the missing image.

### Step 6: Publish to Website

Now update the Daniks.AI website repo at `/Users/ync/poryadok/sources/daniks-ai-ads/`.

#### 6a. Update `src/data/routes.ts`

Add new entry at the TOP of the `blogPosts` array:

```typescript
{
  slug: "[slug]",
  title: "[Full Article Title]",
  date: "[Month DD, YYYY]",
  readTime: "[X] min read",
  category: "[Category]",
  featured: false,
},
```

Calculate read time: word count / 200, rounded to nearest minute.

Category should be one of: `PPC`, `Strategy`, `Research`, `Comparison`, `Reviews`, `Guides`.

#### 6b. Update `src/pages/Blog.tsx`

1. Add image import at the top (after existing imports):
```typescript
import [camelCaseSlug]Image from "@/assets/blog/[slug].jpg";
```

2. Add entry to `blogImages` object:
```typescript
"[slug]": [camelCaseSlug]Image,
```

3. Add entry to `blogExcerpts` object:
```typescript
"[slug]": "[Meta description or first 1-2 sentences as excerpt]",
```

#### 6c. Update `src/pages/BlogPost.tsx`

Add the full article as a new entry in the `blogPostsContent` object. Convert markdown to JSX following these patterns:

**Opening paragraph:**
```jsx
<p className="lead text-xl text-muted-foreground mb-8">
  [First paragraph text]
</p>
```

**Regular paragraphs:**
```jsx
<p className="mb-6">
  [Paragraph text with <strong>bold</strong> and <a href="url" className="text-primary hover:underline">links</a>]
</p>
```

**H2 headings:**
```jsx
<h2 className="text-2xl font-bold mt-10 mb-4">[Heading]</h2>
```

**H3 headings:**
```jsx
<h3 className="text-xl font-semibold mt-8 mb-4">[Heading]</h3>
```

**Bullet lists:**
```jsx
<ul className="list-disc list-inside mb-6 space-y-2 text-muted-foreground">
  <li>[Item text]</li>
  <li><strong>[Bold label]:</strong> [Description]</li>
</ul>
```

**Numbered lists:**
```jsx
<ol className="list-decimal list-inside mb-6 space-y-2 text-muted-foreground">
  <li>[Item text]</li>
</ol>
```

**Pro tip callout:**
```jsx
<div className="bg-primary/5 border-l-4 border-primary p-6 rounded-r-lg my-8">
  <p className="font-medium text-foreground">
    <strong>Pro Tip:</strong> [Tip text]
  </p>
</div>
```

**Note/aside:**
```jsx
<div className="bg-muted/50 p-6 rounded-lg my-8">
  <p className="text-sm text-muted-foreground">
    <strong>Note:</strong> [Note text]
  </p>
</div>
```

**Daniks.AI CTA block:**
```jsx
<div className="bg-gradient-to-r from-primary/10 to-accent/10 p-6 rounded-lg my-8 border border-primary/20">
  <p className="font-medium">
    💡 <strong>Daniks.AI Advantage:</strong> [Product mention text]
  </p>
</div>
```

**Internal links (React Router):**
```jsx
<a href="/blog/[slug]" className="text-primary hover:underline">[anchor text]</a>
```

**External links:**
```jsx
<a href="[url]" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">[anchor text]</a>
```

**Final CTA section at bottom of every article:**
```jsx
<div className="bg-gradient-to-r from-primary/10 to-accent/10 p-8 rounded-lg my-12 border border-primary/20 text-center">
  <h3 className="text-xl font-bold mb-3">Ready to automate your Amazon PPC?</h3>
  <p className="text-muted-foreground mb-4">[CTA supporting text relevant to article topic]</p>
  <a href="https://app.daniks.ai/signup/" target="_blank" rel="noopener noreferrer"
     className="inline-block bg-primary text-primary-foreground px-6 py-3 rounded-lg font-medium hover:opacity-90 transition-opacity">
    Start Your Free 14-Day Trial
  </a>
  <p className="text-sm text-muted-foreground mt-2">14-day free trial · Cancel anytime</p>
</div>
```

### Step 7: Move Draft to Published

Move the draft file from `drafts/` to `published/` in this repo:
```bash
mkdir -p published
mv drafts/[article-file].md published/
```

### Step 8: Commit & Push Website Changes

Commit and push changes in the daniks-ai-ads repo:

```bash
cd /Users/ync/poryadok/sources/daniks-ai-ads

git add src/data/routes.ts src/pages/Blog.tsx src/pages/BlogPost.tsx src/assets/blog/[slug].jpg
git commit -m "Add blog post: [Article Title]"
git push origin main
```

### Step 9: Request Google Indexing

Request Google to crawl and index the new blog post URL immediately:

```bash
python3 data_sources/modules/google_indexing.py "https://daniks.ai/blog/[slug]"
```

This uses the Google Indexing API with the same service account credentials as GSC (`GSC_CREDENTIALS_PATH`). The service account must have owner access in Google Search Console for daniks.ai.

If indexing request fails (credentials missing, API error, permissions issue), log the error and continue — do NOT stop the pipeline.

### Step 10: Publish to LinkedIn Company Page

Cross-post the article to the Daniks.AI LinkedIn company page. The post is published as a native LinkedIn post (not a bare link share) with the featured image attached so it gets the engagement boost LinkedIn gives image posts.

#### 10a. Write the LinkedIn-optimized post

LinkedIn posts that get the most reach follow a different structure than blog content. Write a brand-new piece of copy — do NOT paste the article intro.

Apply these LinkedIn best practices:

- **Hook in the first 2 lines** (max ~210 chars before the "see more" cutoff on mobile). Make people want to expand: a counterintuitive claim, a specific number, a sharp question, or a one-line story setup. Avoid "In this article…" or "I just published…" openings.
- **Short lines + blank lines between them.** No walls of text. Most paragraphs should be 1-2 sentences.
- **Total length: 1,200–1,800 characters.** Long enough to deliver real value, short enough to stay readable. LinkedIn's algorithm rewards "dwell time" — make people scroll, not bounce.
- **Deliver value in the post itself**, then point to the article. The post should be useful even if no one clicks. Pull 3-5 of the article's most concrete insights (a list, a framework, a contrarian take) and rewrite them in conversational tone.
- **Native voice, not corporate voice.** First person where possible ("I see this trip up sellers all the time…"), Daniks.AI brand voice from `context/brand-voice.md`. No buzzwords ("synergy," "leverage," "unlock"), no AI-tells ("delve," "landscape," "in today's").
- **One clear CTA at the end** pointing to the full article — phrase it as a benefit, not "click here". Example: `Full breakdown with the exact ACoS formula → https://daniks.ai/blog/[slug]`
- **3–5 hashtags on the last line**, lowercase or camelCase, mixing one broad (#AmazonFBA, #Ecommerce) with niche tags (#AmazonPPC, #AmazonSellers, #AmazonAdvertising). No more than 5 — diminishing returns.
- **No @mentions** unless the article cites a specific person/company we want to tag.
- **Plain text only.** LinkedIn does not render Markdown — no `**bold**`, no `#headings`, no `[links](url)`. Use line breaks and emoji sparingly (✅ 1–2 max, ❌ never spam them) for visual rhythm.

Save the LinkedIn copy to `published/[slug]-linkedin.txt` (UTF-8, no frontmatter, just the post body).

#### 10b. Publish via the LinkedIn API

```bash
python3 data_sources/modules/linkedin_publisher.py \
  --text-file "published/[slug]-linkedin.txt" \
  --image "/Users/ync/poryadok/sources/daniks-ai-ads/src/assets/blog/[slug].jpg" \
  --link "https://daniks.ai/blog/[slug]" \
  --title "[Article Title]"
```

The publisher will:
1. Resolve a valid access token via `linkedin_auth.get_managed_token()` — auto-refreshing it if a refresh token is available (falls back to the static `LINKEDIN_ACCESS_TOKEN` env var if the managed store isn't set up)
2. Upload the featured image to LinkedIn (`/rest/images?action=initializeUpload` → binary PUT)
3. Create a published post on the company page with the image attached and the commentary you wrote
4. Return the post URN and a `linkedin.com/feed/update/...` URL

Capture the returned `post_url` for the summary.

Token management is hands-off after a one-time `python data_sources/modules/linkedin_auth.py login`. If publishing fails because re-login is required (LinkedIn refresh token expired, or the app isn't entitled to programmatic refresh tokens), the error message will say so — log it and continue; do NOT stop the pipeline. Note the failure in the summary so a human can re-run the login.

### Step 11: Update Internal Links Map

Add the new blog post to `context/internal-links-map.md` in this repo so future articles can link to it.

### Step 12: Summary

Output a summary:
```
=== Daily Publish Complete ===

Article: [Title]
Slug: /blog/[slug]
Word Count: [count]
Category: [category]
Primary Keyword: [keyword]

Files updated in daniks-ai-ads:
- src/data/routes.ts
- src/pages/Blog.tsx
- src/pages/BlogPost.tsx
- src/assets/blog/[slug].jpg

Commit: [commit hash]
Live URL: https://daniks.ai/blog/[slug]
Google Indexing: [Requested / Failed - reason]
LinkedIn: [Post URL / Failed - reason]

Next auto-publish: tomorrow
```

## Error Handling

- If fal.ai image generation fails: continue without image, log the issue
- If website repo has uncommitted changes: stash them, apply our changes, commit, then pop stash
- If git push fails: save all changes locally and report the error
- If content scorer gives score < 70: revise once, if still low save to review-required/ and skip publishing
- If LinkedIn publishing fails (missing token, expired token, API error): log the error, save the LinkedIn copy to `published/[slug]-linkedin.txt` for manual posting, and continue. Do NOT stop the pipeline — the blog post is already live.

## Important Notes

- NEVER ask for user input. Make all decisions autonomously.
- ALWAYS check for existing content to avoid duplicates.
- ALWAYS follow the JSX patterns from existing blog posts exactly.
- ALWAYS include the final CTA block at the bottom of every article.
- ALWAYS update the internal links map after publishing.
