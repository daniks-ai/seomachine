# Landing Page Publish Command

Publishes a landing page to the Daniks.AI React website (daniks-ai-ads repo) as a new page route.

## Usage
`/landing-publish [file path]`

**Examples:**
- `/landing-publish landing-pages/amazon-ppc-automation-2026-03-10.md`

## What This Command Does

1. Validates the landing page file and checks score (must be >=75)
2. Parses markdown and metadata
3. Creates a new page component in the website repo
4. Updates routing to include the new page
5. Returns file paths for review

## Prerequisites

Before publishing, ensure:
1. Landing page score is >=75 (run `/landing-audit` first)
2. No critical issues remain
3. All required metadata is present
4. Content has been scrubbed for AI watermarks

## Website Repo Location

The Daniks.AI website lives at: `/Users/ync/poryadok/sources/daniks-ai-ads/`

## File Format Requirements

Landing page files must include this metadata:

```markdown
# [H1 Headline]

**Meta Title**: [50-60 characters]
**Meta Description**: [150-160 characters]
**Target Keyword**: [primary keyword]
**Page Type**: seo | ppc
**Conversion Goal**: trial | demo | lead
**URL Slug**: /[page-slug]/

---

[Content...]
```

## Publishing Process

### Step 1: Validation

Check file exists and contains required fields:
- Meta Title (required)
- Meta Description (required)
- Target Keyword (required for SEO pages)
- URL Slug

### Step 2: Score Check

Review the landing page against CRO best practices:
- Headline is benefit-focused
- Clear value proposition
- CTAs use action verbs
- Trust signals present
- Risk reversal near CTAs

### Step 3: Create Page Component

Create a new React component at `src/pages/[PageName].tsx` in the website repo following the existing page component patterns (see `AffiliateProgram.tsx` or `Index.tsx` for reference).

**JSX formatting rules** (same as blog posts):
- `<h2>` -> `<h2 className="text-2xl font-bold mt-10 mb-4">`
- `<h3>` -> `<h3 className="text-xl font-semibold mt-8 mb-4">`
- `<p>` -> `<p className="mb-6">`
- Include Header and Footer components
- Use existing UI components (Card, Button, etc.)

### Step 4: Update Routing

Add the new page route to:
1. `src/AppRoutes.tsx` - Add route and lazy import
2. `src/data/routes.ts` - Add to staticRoutes for sitemap

### Step 5: Move to Published

Move the landing page file from `landing-pages/` to `published/` in this repo.

### Step 6: Summary

Display:
- Files created/modified in daniks-ai-ads
- Landing page URL: `https://daniks.ai/[slug]`
- Reminder to add images if needed
- Reminder to commit and deploy

## Differences from /publish-draft

| Aspect | /publish-draft (Blog) | /landing-publish (Pages) |
|--------|----------------------|--------------------------|
| Location | Added to BlogPost.tsx | New page component |
| Route | /blog/[slug] | /[slug] |
| Score Required | Content score >=70 | Landing page score >=75 |
| Template | Follows BlogPost pattern | Standalone page component |
| Navigation | Listed on /blog | Not in main nav (standalone) |

## Pre-Publish Checklist

Before running this command, verify:

### Content
- [ ] Headline is benefit-focused
- [ ] Value proposition is clear
- [ ] CTAs use action verbs
- [ ] Trust signals present
- [ ] Risk reversal near CTAs
- [ ] FAQ section (for SEO pages)

### Meta
- [ ] Meta title 50-60 characters
- [ ] Meta title includes keyword
- [ ] Meta description 150-160 characters
- [ ] URL slug is clean and short

### Technical
- [ ] Content scrubbed for AI watermarks
- [ ] Landing page score >=75
- [ ] No critical issues
- [ ] Proper markdown formatting

## Post-Publish Tasks

After publishing to the website repo:

1. **Review locally** - Run the dev server to verify the page renders correctly
2. **Add visuals** - Hero images, trust badges, screenshots
3. **Test CTAs** - Verify all links and buttons work
4. **Commit & deploy** - Push changes to the website repo
5. **Verify live** - Check the deployed page

## Integration with Other Commands

**Typical Workflow:**
```bash
# 1. Research
/landing-research "amazon ppc automation" --type seo

# 2. Create landing page
/landing-write "amazon ppc automation" --type seo --goal trial

# 3. Audit the draft
/landing-audit landing-pages/amazon-ppc-automation-2026-03-10.md

# 4. Fix any issues, re-audit until score >=75

# 5. Publish
/landing-publish landing-pages/amazon-ppc-automation-2026-03-10.md
```
