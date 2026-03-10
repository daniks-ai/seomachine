# Publish Draft to Daniks.AI Website

Publishes a draft article from this project to the Daniks.AI React website (daniks-ai-ads repo).

## Usage
`/publish-draft [filename]`

### Examples

```
/publish-draft drafts/amazon-ppc-automation-guide-2026-03-10.md
```

## What This Command Does

1. **Parses the draft file** - Extracts all metadata from frontmatter and content
2. **Converts Markdown to JSX** - Transforms the article content into React JSX matching the existing blog post format
3. **Updates the website repo** - Modifies the necessary files in the daniks-ai-ads project
4. **Provides review instructions** - Shows what was changed and how to verify

## Website Repo Location

The Daniks.AI website lives at: `/Users/ync/poryadok/sources/daniks-ai-ads/`

## Files That Need Updating

When publishing a new blog post, these files must be modified:

### 1. `src/data/routes.ts`
Add new blog post metadata to the `blogPosts` array (at the TOP, newest first):

```typescript
{
  slug: "url-slug-from-draft",
  title: "Full Article Title from H1",
  date: "Month DD, YYYY",
  readTime: "X min read",
  category: "Category",
  featured: false,
}
```

**Category options** (based on existing posts): `PPC`, `Strategy`, `Research`, `Comparison`, `Reviews`

### 2. `src/pages/BlogPost.tsx`
Add the full article content as JSX inside the `blogPostsContent` object. Follow the exact formatting patterns used by existing posts:

**JSX formatting rules:**
- `<h2>` → `<h2 className="text-2xl font-bold mt-10 mb-4">`
- `<h3>` → `<h3 className="text-xl font-semibold mt-8 mb-4">`
- `<p>` → `<p className="mb-6">` (or `<p className="lead text-xl text-muted-foreground mb-8">` for the intro paragraph)
- `<ul>` → `<ul className="list-disc list-inside mb-6 space-y-2 text-muted-foreground">`
- `<ol>` → `<ol className="list-decimal list-inside mb-6 space-y-2 text-muted-foreground">`
- `<strong>` for bold text within paragraphs
- Pro tips / callouts → `<div className="bg-primary/5 border-l-4 border-primary p-6 rounded-r-lg my-8">`
- Notes / asides → `<div className="bg-muted/50 p-6 rounded-lg my-8">`
- Daniks.AI product mentions → `<div className="bg-gradient-to-r from-primary/10 to-accent/10 p-6 rounded-lg my-8 border border-primary/20">`
- CTA buttons → use the existing CTA pattern at the bottom of posts
- Internal links → `<a href="/blog/slug" className="text-primary hover:underline">`
- External links → `<a href="url" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">`

### 3. `src/pages/Blog.tsx`
- Add image import at the top of the file
- Add entry to `blogImages` object
- Add excerpt to `blogExcerpts` object

### 4. Blog post image
- A featured image should be placed in `src/assets/blog/`
- Image naming convention: descriptive-slug-name.jpg
- If no image is available yet, note this for the user to add later

## Metadata Mapping

| Draft Field | Website Field |
|-------------|--------------|
| H1 Title | `title` in routes.ts + `title` in BlogPost.tsx |
| URL Slug | `slug` in routes.ts |
| Meta Title | `<title>` tag (handled by SSR) |
| Meta Description | Used as excerpt in Blog.tsx |
| Target Keyword | For reference only (not stored separately) |
| Category | `category` in routes.ts |
| Content | JSX in BlogPost.tsx |

## Process

When you run this command:

### Step 1: Validate & Parse
- Confirm the draft file exists in this repo
- Parse all metadata (title, slug, meta description, category, keyword)
- Extract and display the article structure for confirmation
- Estimate read time based on word count (~200 words per minute)

### Step 2: Convert Markdown to JSX
- Convert all markdown headings, paragraphs, lists, bold text, links to JSX with correct Tailwind classes
- Apply the correct component patterns from existing blog posts
- Preserve internal links as React Router links
- Convert external links with target="_blank"
- Add Daniks.AI CTA block at the end if not already present

### Step 3: Update Website Files
Modify these files in `/Users/ync/poryadok/sources/daniks-ai-ads/`:

1. **`src/data/routes.ts`** - Add BlogPostMeta entry at top of array
2. **`src/pages/BlogPost.tsx`** - Add content entry to blogPostsContent object
3. **`src/pages/Blog.tsx`** - Add image import, blogImages entry, blogExcerpts entry

### Step 4: Move Draft to Published
- Move the draft from `drafts/` to `published/` in this repo
- Note: The user still needs to commit and deploy the website changes

### Step 5: Provide Summary
Display:
- Files modified in daniks-ai-ads
- Blog post URL: `https://daniks.ai/blog/[slug]`
- Reminder to add featured image if not provided
- Reminder to commit and deploy changes in the website repo

## Image Handling

Since this is a static React site, images must be imported as modules:
- Place image in `src/assets/blog/`
- Add import statement in `Blog.tsx`
- Reference in `blogImages` object

If no image is ready, create a placeholder comment and remind the user.

## Notes

- Articles are added directly to the codebase (not via API)
- Changes require a git commit and deploy in the daniks-ai-ads repo
- The user is responsible for reviewing JSX output before committing
- Always add new posts at the TOP of the blogPosts array (newest first)
- Read time calculation: total words / 200, rounded to nearest minute
- Keep the first paragraph of the article as the "lead" paragraph with special styling
