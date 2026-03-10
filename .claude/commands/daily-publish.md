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

### Step 2: Research

Read these context files to inform the article:
- `context/brand-voice.md` - Voice and tone
- `context/features.md` - Product details for natural mentions
- `context/seo-guidelines.md` - SEO requirements
- `context/style-guide.md` - Formatting standards
- `context/writing-examples.md` - Style reference
- `context/target-keywords.md` - Keywords to target
- `context/internal-links-map.md` - Internal links to include
- `context/competitor-analysis.md` - Competitive context

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
  <p className="text-sm text-muted-foreground mt-2">No credit card required</p>
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

### Step 9: Update Internal Links Map

Add the new blog post to `context/internal-links-map.md` in this repo so future articles can link to it.

### Step 10: Summary

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

Next auto-publish: tomorrow
```

## Error Handling

- If fal.ai image generation fails: continue without image, log the issue
- If website repo has uncommitted changes: stash them, apply our changes, commit, then pop stash
- If git push fails: save all changes locally and report the error
- If content scorer gives score < 70: revise once, if still low save to review-required/ and skip publishing

## Important Notes

- NEVER ask for user input. Make all decisions autonomously.
- ALWAYS check for existing content to avoid duplicates.
- ALWAYS follow the JSX patterns from existing blog posts exactly.
- ALWAYS include the final CTA block at the bottom of every article.
- ALWAYS update the internal links map after publishing.
