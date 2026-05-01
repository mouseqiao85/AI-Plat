# Running Custom Playwright Code

Use `run-code` to execute arbitrary Playwright code for advanced scenarios not covered by CLI commands.

## Syntax

```bash
playwright-cli run-code "async page => {
  // Your Playwright code here
  // Access page.context() for browser context operations
}"
```

## Wait Strategies（等待页面加载）

playwright-cli 没有内建的 `wait selector` 命令，用 `run-code` 实现等待：

```bash
# 等待网络空闲（SPA 渲染完成）
playwright-cli run-code "async page => { await page.waitForLoadState('networkidle'); }"

# 等待特定元素出现
playwright-cli run-code "async page => { await page.locator('.loading').waitFor({ state: 'hidden' }); }"

# 等待自定义条件
playwright-cli run-code "async page => { await page.waitForFunction(() => window.appReady === true); }"

# 等待元素出现（带超时）
playwright-cli run-code "async page => { await page.locator('.result').waitFor({ timeout: 10000 }); }"
```

## Geolocation

```bash
playwright-cli run-code "async page => {
  await page.context().grantPermissions(['geolocation']);
  await page.context().setGeolocation({ latitude: 37.7749, longitude: -122.4194 });
}"
```

## Page Information

```bash
playwright-cli run-code "async page => { return await page.title(); }"
playwright-cli run-code "async page => { return page.url(); }"
playwright-cli run-code "async page => { return await page.content(); }"
playwright-cli run-code "async page => { return page.viewportSize(); }"
```

## Frames and Iframes

```bash
playwright-cli run-code "async page => {
  const frame = page.locator('iframe#my-iframe').contentFrame();
  await frame.locator('button').click();
}"
```

## File Downloads

```bash
playwright-cli run-code "async page => {
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download' }).click();
  const download = await downloadPromise;
  await download.saveAs('./downloaded-file.pdf');
  return download.suggestedFilename();
}"
```

## JavaScript Execution

```bash
playwright-cli run-code "async page => {
  return await page.evaluate(() => ({
    userAgent: navigator.userAgent,
    language: navigator.language,
    cookiesEnabled: navigator.cookieEnabled
  }));
}"
```

## Error Handling

```bash
playwright-cli run-code "async page => {
  try {
    await page.getByRole('button', { name: 'Submit' }).click({ timeout: 1000 });
    return 'clicked';
  } catch (e) {
    return 'element not found';
  }
}"
```

## Complex Workflows

```bash
# Scrape data from multiple pages
playwright-cli run-code "async page => {
  const results = [];
  for (let i = 1; i <= 3; i++) {
    await page.goto(\`https://example.com/page/\${i}\`);
    const items = await page.locator('.item').allTextContents();
    results.push(...items);
  }
  return results;
}"
```
