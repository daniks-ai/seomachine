# Daily Auto-Publish Pipeline

Fully automated pipeline: pick a topic, research, write, translate into every supported language, generate image, publish to website, commit & push.

## Usage
This command is designed to run unattended via `claude -p`. Do NOT ask the user any questions. Make all decisions autonomously.

## Multi-Language Requirement

The Daniks.AI website is multi-language. **Every new blog post must be created in ALL supported languages**, not English only. The single source of truth for the supported languages is the `LOCALES` array in `/Users/ync/poryadok/sources/daniks-ai-ads/src/i18n/locales.ts`.

At the time of writing, `LOCALES = ["en", "es", "de", "ru", "pt", "zh", "ja"]`:

| Locale | Language | URL prefix |
|--------|----------|------------|
| `en`   | English (default, canonical) | none — `https://daniks.ai/blog/[slug]` |
| `es`   | Spanish  | `/es` |
| `de`   | German   | `/de` |
| `ru`   | Russian  | `/ru` |
| `pt`   | Portuguese (BR) | `/pt` |
| `zh`   | Simplified Chinese | `/zh` |
| `ja`   | Japanese | `/ja` |

**Always re-read `locales.ts` at run time** and generate the post for whatever locales `LOCALES` contains — if a locale is added or removed later, this pipeline must follow automatically without editing this command.

English (`en`) is the **canonical** version: research it, write it, scrub it, then translate that finished article into every other locale. The slug, image, date, category, read time, and `featured` flag are **shared across all locales** — only the article body and the title/excerpt are translated.

**LinkedIn is the one exception:** the LinkedIn post stays English and links to the English article. See Step 11.

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

### Step 3: Write the English Article (Canonical)

Write a complete, SEO-optimized article in **English** following ALL requirements from the `/write` command. This is the canonical version that every translation is derived from.

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

Decide the **shared metadata** now, because it is reused by every locale:
- **slug** — kebab-case, lowercase, hyphens only. Identical across all locales (the locale prefix in the URL is the only thing that changes).
- **category** — one of: `PPC`, `Strategy`, `Research`, `Comparison`, `Reviews`, `Guides`.
- **readMinutes** — word count / 200, rounded to the nearest whole number (integer).
- **date** — today in ISO format `YYYY-MM-DD`.
- **featured** — `false` (unless deliberately promoting this post).

Save the English article to: `drafts/[slug]-[YYYY-MM-DD].md`

### Step 4: Scrub AI Watermarks

Run the content scrubber on the English draft to remove AI signatures:
```bash
python data_sources/modules/content_scrubber.py drafts/[article-file].md
```

If the scrubber script is not available, manually ensure:
- No invisible Unicode characters
- Em-dashes replaced with appropriate punctuation where overused
- No telltale AI phrases ("delve", "landscape", "it's important to note", "in today's")

The translations you produce in Step 6 must be just as clean — no AI-tells in any language.

### Step 5: Generate Featured Image

Generate ONE blog featured image using fal.ai. The image is **shared across all locales** — generate it once.

```bash
python data_sources/modules/image_generator.py "[Article Title]" \
  --slug "[article-slug]" \
  --output "/Users/ync/poryadok/sources/daniks-ai-ads/src/assets/blog/" \
  --topic "[brief topic description for image prompt]"
```

The image will be saved to `daniks-ai-ads/src/assets/blog/[slug].jpg`.

If image generation fails (no FAL_KEY, API error), continue with the pipeline but note the missing image.

### Step 6: Translate Into Every Supported Language

Read `LOCALES` from `/Users/ync/poryadok/sources/daniks-ai-ads/src/i18n/locales.ts`. English is already written (Step 3). For **every other locale** in `LOCALES` (currently `es`, `de`, `ru`, `pt`, `zh`, `ja`), produce a full, native-quality translation of:

1. The **article body** (the entire post).
2. The **meta title** (keep it SEO-tight, natural in the target language — don't just transliterate the English).
3. The **meta excerpt** (1-2 sentence description in the target language).

Translation rules:

- **Translate meaning, not words.** Write like a native Amazon-seller marketer in that language. Keep the Daniks.AI brand voice, hooks, and mini-stories — adapt idioms and examples so they land naturally.
- **Keep the slug identical** across all locales. Do NOT translate the slug.
- **Keep technical/product terms** that sellers use in English as-is where that's the norm (e.g. ACoS, TACoS, Buy Box, Sponsored Products, Broad/Phrase/Exact match, PPC, ASIN, Daniks.AI). Translate the surrounding prose.
- **Localize internal blog links to the target locale.** In the English body an internal link is `/blog/[target-slug]`. In every non-English locale it must be prefixed with the locale: `/{locale}/blog/[target-slug]` (e.g. German → `/de/blog/amazon-ppc-audit`). English (default) links stay unprefixed.
- **Leave external links unchanged** in every locale — the same absolute URLs (e.g. `https://app.daniks.ai/signup/`, `https://advertising.amazon.com/...`). Do NOT prefix or translate external URLs.
- **Translate the on-page CTA copy** (headings, button labels, supporting text) into the target language, but keep the signup URL identical.
- **Currency and numbers:** keep USD figures and metrics consistent with the English source unless a localized example is clearly more natural; never change the underlying math.

You will write these translations directly into the website files in Step 7 — you don't need separate draft files for them.

### Step 7: Publish to Website (All Locales)

Update the Daniks.AI website repo at `/Users/ync/poryadok/sources/daniks-ai-ads/`.

Blog content now lives in a per-locale content architecture. **Do NOT touch** `src/pages/Blog.tsx`, `src/pages/BlogPost.tsx`, `src/pages/localizedPages.ts`, `server.js`, `public/llms.txt`, or any sitemap file — routing, the sitemap, and hreflang alternates are generated automatically from the files below. The old single-file `BlogPost.tsx` content-object model is retired; do not re-introduce it.

For ONE new post you create/edit exactly these files:

#### 7a. `src/data/routes.ts` — the shared post index (edit)

Add ONE `BlogPostInfo` entry at the TOP of the `blogPosts` array (newest first). This entry is shared by all locales — it has **no title** (titles live in the meta files) and uses `readMinutes` (a number) and an ISO `date`:

```typescript
export const blogPosts: BlogPostInfo[] = [
  {
    slug: "[slug]",
    date: "[YYYY-MM-DD]",
    readMinutes: [integer],
    category: "[PPC | Strategy | Research | Comparison | Reviews | Guides]",
    featured: false,
  },
  // ...existing entries stay below
];
```

#### 7b. `src/content/blog/images.ts` — the shared image map (edit)

1. Add an import at the top with the rest of the image imports:
```typescript
import [camelCaseSlug]Image from "@/assets/blog/[slug].jpg";
```
2. Add an entry at the top of the `blogImages` object:
```typescript
"[slug]": [camelCaseSlug]Image,
```
The image is shared across all locales — one import, one entry.

#### 7c. `src/content/blog/meta/[locale].ts` — translated title + excerpt (edit one per locale)

For **every** locale in `LOCALES`, add an entry keyed by slug to that locale's meta map. Each file looks like:

```typescript
import type { BlogMetaMap } from "../registry";

const meta: BlogMetaMap = {
  "[slug]": {
    title: "[Title translated for this locale]",
    excerpt: "[Excerpt translated for this locale]",
  },
  // ...existing entries
};

export default meta;
```

- `meta/en.ts` gets the English title/excerpt; each other locale gets its translation.
- **If a locale's meta file does not exist yet** (e.g. `meta/ja.ts` may be missing), CREATE it with the header above (`import type { BlogMetaMap } from "../registry";` … `export default meta;`) and add the single entry.

#### 7d. `src/content/blog/[locale]/[slug].tsx` — the article body (create one per locale)

Create one body file per locale at `src/content/blog/[locale]/[slug].tsx`, using the **same slug filename** in every locale directory. Each file has NO imports — it declares a `content` JSX fragment and default-exports it:

```tsx
const content = (
  <>
    {/* article JSX here */}
  </>
);

export default content;
```

Convert the (translated) article to JSX using these patterns:

**Opening / lead paragraph:**
```jsx
<p className="lead text-xl text-muted-foreground mb-8">[First paragraph]</p>
```

**Regular paragraphs:**
```jsx
<p className="mb-6">[Text with <strong>bold</strong>, <em>emphasis</em>, and <code>code</code>]</p>
```

**H2 / H3 headings:**
```jsx
<h2 className="text-2xl font-bold mt-10 mb-4">[Heading]</h2>
<h3 className="text-xl font-semibold mt-8 mb-4">[Heading]</h3>
```

**Bullet / numbered lists:**
```jsx
<ul className="list-disc list-inside mb-6 space-y-2 text-muted-foreground">
  <li><strong>[Label]:</strong> [Description]</li>
</ul>
<ol className="list-decimal list-inside mb-6 space-y-2 text-muted-foreground">
  <li>[Item]</li>
</ol>
```

**Comparison table:**
```jsx
<div className="overflow-x-auto my-8">
  <table className="w-full text-sm border-collapse">
    <thead>
      <tr className="border-b border-border">
        <th className="text-left p-3 font-semibold">[Col]</th>
      </tr>
    </thead>
    <tbody className="text-muted-foreground">
      <tr className="border-b border-border">
        <td className="p-3 font-medium text-foreground">[Row label]</td>
        <td className="p-3">[Cell]</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Pro tip callout:**
```jsx
<div className="bg-primary/5 border-l-4 border-primary p-6 rounded-r-lg my-8">
  <p className="font-medium text-foreground"><strong>Pro Tip:</strong> [Tip]</p>
</div>
```

**Note / aside:**
```jsx
<div className="bg-muted/50 p-6 rounded-lg my-8">
  <p className="text-sm text-muted-foreground"><strong>Note:</strong> [Note]</p>
</div>
```

**Daniks.AI advantage block:**
```jsx
<div className="bg-gradient-to-r from-primary/10 to-accent/10 p-6 rounded-lg my-8 border border-primary/20">
  <p className="font-medium">💡 <strong>Daniks.AI Advantage:</strong> [Product mention]</p>
</div>
```

**Internal links (locale-prefixed for non-English):**
```jsx
{/* English (en): */}    <a href="/blog/[slug]" className="text-primary hover:underline">[anchor]</a>
{/* Non-English ({locale}): */} <a href="/{locale}/blog/[slug]" className="text-primary hover:underline">[anchor]</a>
```

**External links (identical in every locale):**
```jsx
<a href="[url]" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">[anchor]</a>
```

**Final CTA section at the bottom of every article (translate the copy, keep the URL):**
```jsx
<div className="bg-gradient-to-r from-primary/10 to-accent/10 p-8 rounded-lg my-12 border border-primary/20 text-center">
  <h3 className="text-xl font-bold mb-3">[Ready to automate your Amazon PPC? — translated]</h3>
  <p className="text-muted-foreground mb-4">[CTA supporting text — translated]</p>
  <a href="https://app.daniks.ai/signup/" target="_blank" rel="noopener noreferrer"
     className="inline-block bg-primary text-primary-foreground px-6 py-3 rounded-lg font-medium hover:opacity-90 transition-opacity">
    [Start Your Free 14-Day Trial — translated]
  </a>
  <p className="text-sm text-muted-foreground mt-2">[14-day free trial · Cancel anytime — translated]</p>
</div>
```

Every locale's body must contain the full article — do not leave any locale as a stub. (Missing locales silently fall back to English at runtime, which is exactly what we're avoiding.)

### Step 8: Move Draft to Published

Move the English canonical draft from `drafts/` to `published/` in this repo:
```bash
mkdir -p published
mv drafts/[article-file].md published/
```

### Step 9: Commit & Push Website Changes

Commit and push changes in the daniks-ai-ads repo. Stage the shared files, the per-locale meta files, the per-locale body files, and the image. Use a glob for the locale directories so every language is included:

```bash
cd /Users/ync/poryadok/sources/daniks-ai-ads

git add src/data/routes.ts \
        src/content/blog/images.ts \
        src/content/blog/meta/*.ts \
        src/content/blog/*/[slug].tsx \
        src/assets/blog/[slug].jpg

git commit -m "Add blog post ([N] languages): [Article Title]"
git push origin main
```

Before committing, verify every locale in `LOCALES` has both a `meta/[locale].ts` entry and a `content/blog/[locale]/[slug].tsx` file for the new slug.

### Step 10: Request Google Indexing

Request Google to crawl and index the new post in **every locale** (each language version has its own URL). Build the URL per locale: English has no prefix, every other locale is prefixed with `/{locale}`.

```bash
# English (default)
python3 data_sources/modules/google_indexing.py "https://daniks.ai/blog/[slug]"
# Each other locale (es, de, ru, pt, zh, ja, ...):
python3 data_sources/modules/google_indexing.py "https://daniks.ai/[locale]/blog/[slug]"
```

This uses the Google Indexing API with the same service account credentials as GSC (`GSC_CREDENTIALS_PATH`). The service account must have owner access in Google Search Console for daniks.ai.

If any indexing request fails (credentials missing, API error, permissions, quota), log the error and continue with the remaining URLs — do NOT stop the pipeline.

### Step 11: Publish to LinkedIn Company Page

**LinkedIn posting is unchanged by multi-language: it stays ENGLISH and links to the ENGLISH article** (`https://daniks.ai/blog/[slug]`, no locale prefix). Do NOT translate the LinkedIn post and do NOT link to a localized URL. Post it once, in English.

Cross-post the article to the Daniks.AI LinkedIn company page as a native LinkedIn post (not a bare link share) with the featured image attached so it gets the engagement boost LinkedIn gives image posts.

#### 11a. Write the LinkedIn-optimized post (English)

LinkedIn posts that get the most reach follow a different structure than blog content. Write a brand-new piece of copy — do NOT paste the article intro.

Apply these LinkedIn best practices:

- **Hook in the first 2 lines** (max ~210 chars before the "see more" cutoff on mobile). Make people want to expand: a counterintuitive claim, a specific number, a sharp question, or a one-line story setup. Avoid "In this article…" or "I just published…" openings.
- **Short lines + blank lines between them.** No walls of text. Most paragraphs should be 1-2 sentences.
- **Total length: 1,200–1,800 characters.** Long enough to deliver real value, short enough to stay readable. LinkedIn's algorithm rewards "dwell time" — make people scroll, not bounce.
- **Deliver value in the post itself**, then point to the article. The post should be useful even if no one clicks. Pull 3-5 of the article's most concrete insights (a list, a framework, a contrarian take) and rewrite them in conversational tone.
- **Native voice, not corporate voice.** First person where possible ("I see this trip up sellers all the time…"), Daniks.AI brand voice from `context/brand-voice.md`. No buzzwords ("synergy," "leverage," "unlock"), no AI-tells ("delve," "landscape," "in today's").
- **One clear CTA at the end** pointing to the full **English** article — phrase it as a benefit, not "click here". Example: `Full breakdown with the exact ACoS formula → https://daniks.ai/blog/[slug]`
- **3–5 hashtags on the last line**, lowercase or camelCase, mixing one broad (#AmazonFBA, #Ecommerce) with niche tags (#AmazonPPC, #AmazonSellers, #AmazonAdvertising). No more than 5 — diminishing returns.
- **No @mentions** unless the article cites a specific person/company we want to tag.
- **Plain text only.** LinkedIn does not render Markdown — no `**bold**`, no `#headings`, no `[links](url)`. Use line breaks and emoji sparingly (✅ 1–2 max, ❌ never spam them) for visual rhythm.

Save the LinkedIn copy to `published/[slug]-linkedin.txt` (UTF-8, no frontmatter, just the post body).

#### 11b. Publish via the LinkedIn API

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

### Step 12: Update Internal Links Map

Add the new blog post to `context/internal-links-map.md` in this repo so future articles can link to it. Record the English URL (`https://daniks.ai/blog/[slug]`); the localized URLs follow the `/{locale}/blog/[slug]` pattern automatically.

### Step 13: Summary

Output a summary:
```
=== Daily Publish Complete ===

Article: [Title]
Slug: /blog/[slug]
Word Count: [count]
Read Time: [readMinutes] min
Category: [category]
Primary Keyword: [keyword]

Languages published: [en, es, de, ru, pt, zh, ja]
Per-locale URLs:
- EN: https://daniks.ai/blog/[slug]
- ES: https://daniks.ai/es/blog/[slug]
- DE: https://daniks.ai/de/blog/[slug]
- RU: https://daniks.ai/ru/blog/[slug]
- PT: https://daniks.ai/pt/blog/[slug]
- ZH: https://daniks.ai/zh/blog/[slug]
- JA: https://daniks.ai/ja/blog/[slug]

Files updated in daniks-ai-ads:
- src/data/routes.ts
- src/content/blog/images.ts
- src/content/blog/meta/[locale].ts  (one per language)
- src/content/blog/[locale]/[slug].tsx  (one per language)
- src/assets/blog/[slug].jpg

Commit: [commit hash]
Google Indexing: [Requested for N/N locale URLs / partial - reasons]
LinkedIn (English): [Post URL / Failed - reason]

Next auto-publish: tomorrow
```

## Error Handling

- If fal.ai image generation fails: continue without image, log the issue
- If a translation for a locale can't be produced for some reason: still create that locale's files with the best available content — never leave a locale file missing while others exist, and never ship a stub. If truly blocked, log it clearly in the summary.
- If website repo has uncommitted changes: stash them, apply our changes, commit, then pop stash
- If git push fails: save all changes locally and report the error
- If content scorer gives score < 70 on the English article: revise once, if still low save to `review-required/` and skip publishing (all languages)
- If a Google Indexing request fails for one locale: log it, continue with the other locale URLs
- If LinkedIn publishing fails (missing token, expired token, API error): log the error, save the LinkedIn copy to `published/[slug]-linkedin.txt` for manual posting, and continue. Do NOT stop the pipeline — the blog post is already live.

## Important Notes

- NEVER ask for user input. Make all decisions autonomously.
- ALWAYS create the post in EVERY locale listed in `src/i18n/locales.ts` `LOCALES` — re-read that file at run time; do not hard-code the language list.
- The slug, image, date, category, `readMinutes`, and `featured` flag are SHARED across locales; only the body and title/excerpt are translated.
- Internal blog links inside a locale's body must be prefixed with that locale (`/de/blog/...`); English uses no prefix. External links are identical in every locale.
- LinkedIn stays ENGLISH and links to the ENGLISH article — never translate or localize the LinkedIn post.
- ALWAYS check for existing content to avoid duplicates.
- ALWAYS follow the JSX patterns from existing blog posts exactly, and default-export the `content` fragment.
- ALWAYS include the final CTA block at the bottom of every article, in every language.
- Do NOT edit `src/pages/Blog.tsx`, `src/pages/BlogPost.tsx`, `src/pages/localizedPages.ts`, `server.js`, `public/llms.txt`, or the sitemap — the sitemap and hreflang alternates are generated automatically from `routes.ts` + `LOCALES`.
- ALWAYS update the internal links map after publishing.
