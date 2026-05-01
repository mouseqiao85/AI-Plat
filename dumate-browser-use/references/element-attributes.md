# Inspecting Element Attributes

When the snapshot doesn't show an element's `id`, `class`, `data-*` attributes, or other DOM properties, use `eval` to inspect them.

## Examples

```bash
playwright-cli snapshot
# snapshot shows a button as e7 but doesn't reveal its id or data attributes

# get the element's id
playwright-cli eval "el => el.id" e7

# get all CSS classes
playwright-cli eval "el => el.className" e7

# get a specific attribute
playwright-cli eval "el => el.getAttribute('data-testid')" e7
playwright-cli eval "el => el.getAttribute('aria-label')" e7

# get a computed style property
playwright-cli eval "el => getComputedStyle(el).display" e7

# get element text content
playwright-cli eval "el => el.textContent" e7

# get element's bounding box
playwright-cli eval "el => JSON.stringify(el.getBoundingClientRect())" e7
```

## Tips

- `snapshot` 返回 ARIA 语义树，只显示可访问性相关属性
- 需要原始 DOM 属性（id/class/data-*）时，用 `eval "el => el.xxx" <ref>` 查询
- `eval` 支持 ref 参数，会把对应元素作为 `el` 传入函数
