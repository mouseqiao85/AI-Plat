# 临时和缓存文件说明

## Python缓存文件

`__pycache__` 目录是Python解释器自动生成的缓存目录，包含编译后的字节码文件(.pyc)，用于提高模块加载速度。

### 位置：
- platform/__pycache__/
- platform/agents/__pycache__/
- platform/config/__pycache__/
- platform/examples/__pycache__/
- platform/ontology/__pycache__/
- platform/vibecoding/__pycache__/

### 处理建议：
- 这些目录不应手动删除或移动，因为它们由Python运行时自动管理
- 如果需要清理，可以通过 `python -m compileall -c` 和适当的清理脚本来处理
- 在版本控制系统中通常会忽略这些目录（通过.gitignore）

## 其他可能的临时文件

在项目运行过程中可能会产生其他临时文件，如：
- IDE生成的配置文件
- 日志文件
- 构建输出文件

这些文件通常也应该被版本控制系统忽略。