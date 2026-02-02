# 文档处理器 (Document Processor)

## 用途
这个工具可以帮助您将Word文档(.docx)、PDF文档(.pdf)和其他格式的文档转换为纯文本格式，以便AI可以理解和处理这些文档内容。

## 功能
- 支持 .docx, .pdf, .txt, .md, .rst 等多种格式
- 提取文档中的文本内容（包括表格内容）
- 保留文档结构信息
- 输出为纯文本格式，方便AI处理

## 使用方法

### 方法1：直接运行批处理文件
双击运行 `convert_docx.bat` 文件，它会自动将您的 "融合版_V3.2_概要设计.docx" 文档转换为文本格式。

### 方法2：命令行方式
打开命令提示符，导航到项目目录并运行：

```bash
python utils/document_processor.py "path/to/your/document.docx" "output_file.txt"
```

例如：
```bash
python utils/document_processor.py "C:\Users\qiaoshuowen\Downloads\融合版_V3.2_概要设计.docx" "fusion_design_spec.txt"
```

### 方法3：在Python中直接调用
```python
from utils.document_processor import process_document

# 处理文档
content = process_document("path/to/document.docx", "output.txt")
if content:
    print(f"文档包含 {len(content)} 个字符")
```

## 依赖项
- python-docx (已安装)
- PyPDF2 (如需处理PDF)

## 注意事项
1. 确保文档路径正确
2. 文档内容会被转换为纯文本，格式信息会丢失
3. 表格内容会以 `[TABLE CELL]` 标记形式保留
4. 页眉页脚会以 `[HEADER]` 和 `[FOOTER]` 标记形式保留

## 输出
转换后的文本文件将保存在指定位置，您可以将其内容复制到与AI的对话中，以便AI理解和分析文档内容。