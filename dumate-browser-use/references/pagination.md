# Pagination Strategy

Before paginating, **identify the page's pagination type** and choose the correct method. Wrong methods will fail to load new content.

---

## Step 1: Identify Pagination Type

Determine from the snapshot which pagination method the page uses:

| Type | Detection Signals | Method |
|------|------------------|--------|
| **Infinite scroll** | "Load more" or no pagination controls, content increases as you scroll | `mousewheel` scroll |
| **Page numbers** | Page number digits (1, 2, 3...), "Next"/"Next page"/">" buttons | Click page number or "Next" button |
| **Load more button** | "Load more"/"查看更多" button at bottom | Click the button |
| **Masonry/Waterfall** | E-commerce/social media card layout, no clear pagination | Scroll to bottom and check for new content |

### Common Website Pagination Types

| Website | Pagination Type | Method |
|---------|----------------|--------|
| Taobao search | Page numbers | Click page number or "Next" |
| JD search | Page numbers | Click page number or "Next" |
| Xiaohongshu | Infinite scroll | Scroll to load |
| Douyin | Infinite scroll | Scroll to load |
| Baidu search | Page numbers | Click page number |
| Weibo | Page numbers | Click page number |
| Zhihu | Page numbers | Click page number |
| Amazon | Page numbers | Click page number |
| Bilibili | Page numbers | Click page number or "Next" |

---

## Step 2: Execute Pagination

### Type A: Infinite Scroll / Masonry

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Scroll down
playwright-cli mousewheel 0 800

# Wait for loading, then get new snapshot
sleep 2 && playwright-cli snapshot && _pw_snap
```

**Note**: If content doesn't increase after multiple scrolls, the site may use page numbers. Check the bottom for "Next" buttons.

### Type B: Page Numbers

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Find "Next"/">"/">>" button ref from snapshot
playwright-cli click <ref>   # e.g., playwright-cli click e42

# Wait for page load
sleep 2 && playwright-cli snapshot && _pw_snap
```

**Alternative**: Click specific page number

```shell
# Click page number directly (e.g., "2", "3", "Next")
playwright-cli click <ref>
sleep 2 && playwright-cli snapshot && _pw_snap
```

### Type C: Load More Button

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Find "Load more"/"查看更多" button from snapshot
playwright-cli click <ref>

# Wait for new content
sleep 2 && playwright-cli snapshot && _pw_snap
```

---

## Step 3: Verify Pagination Success

| Pagination Type | Success Signals | Failure Signals |
|----------------|-----------------|-----------------|
| Infinite scroll | Snapshot content increases, new elements appear | Content unchanged after scroll, "No more" message appears |
| Page numbers | URL changes (`page=X`), content updates | "Next" button becomes disabled or disappears |
| Load more | New content loads, button still clickable | "All loaded" message, button disappears |

### Code to Check Pagination Success

```shell
# Method 1: Check URL change (for page-numbered sites)
playwright-cli eval "window.location.href"

# Method 2: Track content count
# Record element count before pagination, compare after

# Method 3: Check "Next" button state
# If button becomes disabled or disappears, last page reached
```

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Scrolling but no new content | Page-numbered site, not infinite scroll | Check snapshot bottom for page numbers/Next button, switch to clicking |
| Clicking Next has no effect | Button may be disabled or needs wait | `sleep 1` before clicking, or scroll to bottom to make button visible |
| Content same after pagination | AJAX-loaded page, URL unchanged | Use `waitForSelector` to wait for new content |
| Don't know if more pages exist | Check "Next" button state | Check if button is disabled before clicking |
| Page number button obscured | Page needs scroll to pagination area | `mousewheel 0 800` to scroll to bottom first |
| Clicking page goes to first page | May not be logged in or triggered anti-bot | Check if login required, reduce operation frequency |

---

## Best Practices

### 1. Identify Type Before Paginating

```shell
# Step 1: Get snapshot, check pagination controls
playwright-cli snapshot && _pw_snap

# Step 2: Determine pagination type from snapshot
# - See "Next"/">"/page numbers → Page numbers
# - See "Load more"/"Load more" button → Load more button
# - No pagination controls at bottom → Likely infinite scroll

# Step 3: Choose correct pagination method
```

### 2. Verify After Pagination

```shell
# Must re-snapshot after paginating to confirm content changed
playwright-cli click <next_page_ref>
sleep 2 && playwright-cli snapshot && _pw_snap

# If content unchanged, pagination may have failed, try another method
```

### 3. Detecting Last Page

```shell
# Page numbers: Check "Next" button state
# - Button disappeared → Last page reached
# - Button disabled (grayed out) → Last page reached

# Infinite scroll: Check for messages
# - "No more"/"All loaded" → Last page reached
# - Content unchanged after 2 consecutive scrolls → May be last page
```

### 4. Recommendations for Heavy Pagination

```shell
# Wait appropriately every few pages to avoid anti-bot triggers
for i in {1..5}; do
    playwright-cli click <next_page_ref>
    sleep 3  # Increase wait time appropriately
    playwright-cli snapshot && _pw_snap
done
```

---

## Example: JD Search Pagination

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# 1. Search and get snapshot
_pw_open "https://search.jd.com/Search?keyword=手机"
playwright-cli snapshot && _pw_snap

# 2. Check pagination type: JD uses page numbers
# Find "Next" button ref from snapshot (usually ">" or "下一页" text)

# 3. Click next page
playwright-cli click <ref>  # e.g., e50 is the next page button

# 4. Wait for load and verify
sleep 2 && playwright-cli snapshot && _pw_snap

# 5. Check if URL or content changed
playwright-cli eval "window.location.href"
# Should see page=2 or similar parameter
```

---

## Example: Taobao Search Pagination

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# 1. Search and get snapshot
_pw_open "https://s.taobao.com/search?q=手机"
playwright-cli snapshot && _pw_snap

# 2. Check pagination type: Taobao uses page numbers
# Find page number or "Next" button from snapshot

# 3. Scroll to bottom to make pagination controls visible
playwright-cli mousewheel 0 800
sleep 1 && playwright-cli snapshot && _pw_snap

# 4. Click next page
playwright-cli click <ref>

# 5. Wait for load
sleep 2 && playwright-cli snapshot && _pw_snap
```

---

## Example: Infinite Scroll Page

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Continuously scroll to load content
for i in {1..10}; do
    # Record current content count
    playwright-cli snapshot && _pw_snap

    # Scroll
    playwright-cli mousewheel 0 800
    sleep 2

    # Get new snapshot, check if content increased
    playwright-cli snapshot && _pw_snap

    # If content no longer increases, exit loop
    # Detection: element count unchanged, or "No more" message appears
done
```

---

## Example: Page Numbers (using JavaScript click)

When refs from snapshot are unstable, use JavaScript to click pagination buttons directly:

### Check Pagination Button State

```shell
# Generic template: check if next button exists and is clickable
playwright-cli eval "() => {
  // Modify selector based on actual page
  const nextBtn = document.querySelector('<next-button-selector>');
  if (!nextBtn) return { hasNext: false, reason: 'button not found' };
  // Check disabled state (modify class name or attribute based on actual page)
  if (nextBtn.classList.contains('<disabled-class>') || nextBtn.disabled) {
    return { hasNext: false, reason: 'button disabled' };
  }
  return { hasNext: true };
}"
```

### Click Next Page

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Generic template: click next page with JavaScript
playwright-cli eval "() => {
  const nextBtn = document.querySelector('<next-button-selector>');
  if (nextBtn && !nextBtn.classList.contains('<disabled-class>')) {
    nextBtn.click();
    return { clicked: true };
  }
  return { clicked: false, reason: 'button disabled or not found' };
}"

# Wait for page load
sleep 3 && playwright-cli snapshot && _pw_snap
```

---

## Example: Batch Pagination and Data Extraction

```shell
source "${_SKILL_DIR}/scripts/session-header.sh"

# Navigate to target page
_pw_open "<target-url>"
playwright-cli snapshot && _pw_snap

# Batch pagination
for page in {1..20}; do
  echo "=== Page ${page} ==="

  # 1. Extract current page data (modify selectors based on actual page)
  data=$(playwright-cli eval "() => {
    const results = [];
    // Modify to actual list item selector
    const items = document.querySelectorAll('<list-item-selector>');
    items.forEach(item => {
      // Modify to actual fields you need
      const title = item.querySelector('<title-selector>')?.textContent.trim();
      const link = item.querySelector('<link-selector>')?.href;
      if (title && link) {
        results.push({ title, link });
      }
    });
    return JSON.stringify(results);
  }")
  echo "$data"

  # 2. Check if there's a next page
  has_next=$(playwright-cli eval "() => {
    const nextBtn = document.querySelector('<next-button-selector>');
    // Check button exists and not disabled
    if (!nextBtn) return 'false';
    if (nextBtn.classList.contains('<disabled-class>') || nextBtn.disabled) return 'false';
    return 'true';
  }")

  if [ "$has_next" = "false" ]; then
    echo "Reached last page"
    break
  fi

  # 3. Click next page
  playwright-cli eval "() => {
    document.querySelector('<next-button-selector>').click();
  }"

  # 4. Wait for load
  sleep 3 && playwright-cli snapshot && _pw_snap
done
```

### Notes

1. **Get selectors**: First `snapshot` to see page structure, find actual pagination element selectors
2. **Wait time**: Use `sleep 3` or longer for complex pages to ensure content loads
3. **Scroll to bottom**: If pagination controls not visible, `mousewheel 0 1000` first
4. **Anti-bot**: Too many page turns may trigger verification, pause a few seconds every 5-10 pages