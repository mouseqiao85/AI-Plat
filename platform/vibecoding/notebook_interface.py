"""
Vibecoding笔记本接口
提供大模型驱动的智能笔记本开发环境
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import logging
import json
import os
import sys
from pathlib import Path
import inspect

from .code_analyzer import CodeAnalyzer, ModuleInfo
from .code_generator import CodeGenerator, GeneratedCode

logger = logging.getLogger(__name__)


@dataclass
class NotebookCell:
    """笔记本单元格数据类"""
    id: str
    cell_type: str  # code, markdown, raw
    content: str
    execution_count: Optional[int] = None
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    executed_at: Optional[datetime] = None
    execution_time: Optional[float] = None


@dataclass
class VibecodingNotebook:
    """Vibecoding笔记本数据类"""
    id: str
    name: str
    description: str
    cells: List[NotebookCell] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)


class VibecodingNotebookInterface:
    """Vibecoding笔记本接口"""
    
    def __init__(self):
        """初始化笔记本接口"""
        self.notebooks: Dict[str, VibecodingNotebook] = {}
        self.code_analyzer = CodeAnalyzer()
        self.code_generator = CodeGenerator()
        self.global_namespace = {}
        
        logger.info("Vibecoding Notebook Interface initialized")
    
    def create_notebook(self, name: str, description: str = "") -> str:
        """
        创建新的笔记本
        
        Args:
            name: 笔记本名称
            description: 笔记本描述
            
        Returns:
            笔记本ID
        """
        notebook_id = str(uuid.uuid4())
        
        notebook = VibecodingNotebook(
            id=notebook_id,
            name=name,
            description=description
        )
        
        self.notebooks[notebook_id] = notebook
        
        logger.info(f"Created notebook: {name} (ID: {notebook_id})")
        return notebook_id
    
    def get_notebook(self, notebook_id: str) -> Optional[VibecodingNotebook]:
        """
        获取笔记本
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            笔记本对象或None
        """
        return self.notebooks.get(notebook_id)
    
    def add_cell(self, 
                 notebook_id: str, 
                 cell_type: str, 
                 content: str, 
                 index: Optional[int] = None) -> str:
        """
        添加单元格到笔记本
        
        Args:
            notebook_id: 笔记本ID
            cell_type: 单元格类型 (code, markdown, raw)
            content: 单元格内容
            index: 插入位置索引
            
        Returns:
            单元格ID
        """
        if notebook_id not in self.notebooks:
            raise ValueError(f"Notebook not found: {notebook_id}")
        
        cell_id = str(uuid.uuid4())
        cell = NotebookCell(id=cell_id, cell_type=cell_type, content=content)
        
        notebook = self.notebooks[notebook_id]
        
        if index is not None and 0 <= index <= len(notebook.cells):
            notebook.cells.insert(index, cell)
        else:
            notebook.cells.append(cell)
        
        notebook.updated_at = datetime.now()
        
        logger.info(f"Added cell to notebook {notebook_id}: {cell_type} cell (ID: {cell_id})")
        return cell_id
    
    def update_cell(self, notebook_id: str, cell_id: str, content: str) -> bool:
        """
        更新单元格内容
        
        Args:
            notebook_id: 笔记本ID
            cell_id: 单元格ID
            content: 新内容
            
        Returns:
            更新是否成功
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return False
        
        for cell in notebook.cells:
            if cell.id == cell_id:
                cell.content = content
                notebook.updated_at = datetime.now()
                return True
        
        return False
    
    def delete_cell(self, notebook_id: str, cell_id: str) -> bool:
        """
        删除单元格
        
        Args:
            notebook_id: 笔记本ID
            cell_id: 单元格ID
            
        Returns:
            删除是否成功
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return False
        
        initial_length = len(notebook.cells)
        notebook.cells = [cell for cell in notebook.cells if cell.id != cell_id]
        
        if len(notebook.cells) < initial_length:
            notebook.updated_at = datetime.now()
            return True
        
        return False
    
    async def execute_cell(self, notebook_id: str, cell_id: str) -> Dict[str, Any]:
        """
        执行单元格
        
        Args:
            notebook_id: 笔记本ID
            cell_id: 单元格ID
            
        Returns:
            执行结果
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook not found: {notebook_id}")
        
        cell = None
        for c in notebook.cells:
            if c.id == cell_id:
                cell = c
                break
        
        if not cell:
            raise ValueError(f"Cell not found: {cell_id}")
        
        if cell.cell_type != 'code':
            return {
                'success': False,
                'error': f'Cannot execute {cell.cell_type} cell',
                'outputs': []
            }
        
        start_time = datetime.now()
        
        try:
            # 执行代码
            outputs = []
            
            # 使用全局命名空间执行代码
            local_vars = self.global_namespace.copy()
            
            # 临时捕获print输出
            import io
            import contextlib
            
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                try:
                    # 尝试作为表达式执行
                    compiled_code = compile(cell.content, '<notebook>', 'eval')
                    result = eval(compiled_code, {"__builtins__": __builtins__}, local_vars)
                    if result is not None:
                        outputs.append({
                            'output_type': 'execute_result',
                            'data': {'text/plain': str(result)},
                            'execution_count': cell.execution_count
                        })
                except SyntaxError:
                    # 如果是语句，执行整个代码块
                    compiled_code = compile(cell.content, '<notebook>', 'exec')
                    exec(compiled_code, {"__builtins__": __builtins__}, local_vars)
            
            # 获取print输出
            print_output = output_buffer.getvalue()
            if print_output.strip():
                outputs.append({
                    'output_type': 'stream',
                    'name': 'stdout',
                    'text': print_output
                })
            
            # 更新全局命名空间
            self.global_namespace.update(local_vars)
            
            # 更新单元格信息
            execution_duration = (datetime.now() - start_time).total_seconds()
            cell.execution_count = getattr(self, '_execution_counter', 0) + 1
            setattr(self, '_execution_counter', cell.execution_count)
            cell.executed_at = datetime.now()
            cell.execution_time = execution_duration
            cell.outputs = outputs
            
            notebook.updated_at = datetime.now()
            
            logger.info(f"Executed cell {cell_id} in {execution_duration:.2f}s")
            
            return {
                'success': True,
                'execution_count': cell.execution_count,
                'execution_time': execution_duration,
                'outputs': outputs
            }
            
        except Exception as e:
            error_output = {
                'output_type': 'error',
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': [str(e)]
            }
            
            cell.outputs = [error_output]
            
            logger.error(f"Error executing cell {cell_id}: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'outputs': [error_output]
            }
    
    async def execute_notebook(self, notebook_id: str) -> Dict[str, Any]:
        """
        执行整个笔记本
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            执行结果
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook not found: {notebook_id}")
        
        results = {
            'notebook_id': notebook_id,
            'executed_cells': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0,
            'cell_results': []
        }
        
        total_start_time = datetime.now()
        
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                cell_result = await self.execute_cell(notebook_id, cell.id)
                results['cell_results'].append({
                    'cell_id': cell.id,
                    'cell_index': notebook.cells.index(cell),
                    'result': cell_result
                })
                
                results['executed_cells'] += 1
                if cell_result['success']:
                    results['successful_executions'] += 1
                else:
                    results['failed_executions'] += 1
                
                if 'execution_time' in cell_result:
                    results['total_execution_time'] += cell_result['execution_time']
        
        results['total_execution_time'] = (datetime.now() - total_start_time).total_seconds()
        
        logger.info(f"Executed notebook {notebook_id}: {results['successful_executions']}/{results['executed_cells']} successful")
        
        return results
    
    def analyze_code_cell(self, notebook_id: str, cell_id: str) -> Optional[ModuleInfo]:
        """
        分析代码单元格
        
        Args:
            notebook_id: 笔记本ID
            cell_id: 单元格ID
            
        Returns:
            代码分析结果
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return None
        
        cell = None
        for c in notebook.cells:
            if c.id == cell_id and c.cell_type == 'code':
                cell = c
                break
        
        if not cell:
            return None
        
        return self.code_analyzer.analyze_code(cell.content, f"{notebook.name}_cell_{cell_id}")
    
    def generate_code_from_prompt(self, 
                                 notebook_id: str, 
                                 prompt: str, 
                                 cell_index: Optional[int] = None) -> str:
        """
        根据提示生成代码并添加到笔记本
        
        Args:
            notebook_id: 笔记本ID
            prompt: 生成提示
            cell_index: 插入位置索引
            
        Returns:
            新单元格ID
        """
        # 生成代码
        generated = self.code_generator.generate_code(prompt)
        
        # 添加到笔记本
        cell_id = self.add_cell(notebook_id, 'code', generated.code, cell_index)
        
        logger.info(f"Generated code from prompt and added to notebook {notebook_id}")
        return cell_id
    
    def get_notebook_variables(self, notebook_id: str) -> Dict[str, Any]:
        """
        获取笔记本中的变量
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            变量字典
        """
        if notebook_id not in self.notebooks:
            return {}
        
        # 返回当前全局命名空间的副本
        return self.global_namespace.copy()
    
    def save_notebook(self, notebook_id: str, file_path: str):
        """
        保存笔记本到文件
        
        Args:
            notebook_id: 笔记本ID
            file_path: 文件路径
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook not found: {notebook_id}")
        
        # 转换为标准笔记本格式
        notebook_data = {
            'metadata': {
                'language_info': {
                    'name': 'python',
                    'version': sys.version
                },
                'orig_nbformat': 4
            },
            'nbformat': 4,
            'nbformat_minor': 4,
            'cells': [
                {
                    'cell_type': cell.cell_type,
                    'metadata': cell.metadata,
                    'source': cell.content.split('\n'),
                    'outputs': cell.outputs,
                    'execution_count': cell.execution_count
                } for cell in notebook.cells
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(notebook_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Saved notebook {notebook_id} to {file_path}")
    
    def load_notebook(self, file_path: str, name: str) -> str:
        """
        从文件加载笔记本
        
        Args:
            file_path: 文件路径
            name: 笔记本名称
            
        Returns:
            笔记本ID
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            notebook_data = json.load(f)
        
        notebook_id = str(uuid.uuid4())
        
        # 转换为内部格式
        cells = []
        for cell_data in notebook_data['cells']:
            cell = NotebookCell(
                id=str(uuid.uuid4()),
                cell_type=cell_data['cell_type'],
                content='\n'.join(cell_data['source']) if isinstance(cell_data['source'], list) else cell_data['source'],
                execution_count=cell_data.get('execution_count'),
                outputs=cell_data.get('outputs', []),
                metadata=cell_data.get('metadata', {})
            )
            cells.append(cell)
        
        notebook = VibecodingNotebook(
            id=notebook_id,
            name=name,
            description=f"Loaded from {file_path}",
            cells=cells,
            metadata=notebook_data.get('metadata', {})
        )
        
        self.notebooks[notebook_id] = notebook
        
        logger.info(f"Loaded notebook from {file_path} with {len(cells)} cells")
        return notebook_id
    
    def get_notebook_summary(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        """
        获取笔记本摘要
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            笔记本摘要
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return None
        
        code_cells = [c for c in notebook.cells if c.cell_type == 'code']
        markdown_cells = [c for c in notebook.cells if c.cell_type == 'markdown']
        raw_cells = [c for c in notebook.cells if c.cell_type == 'raw']
        
        total_execution_time = sum(c.execution_time or 0 for c in code_cells)
        
        return {
            'id': notebook.id,
            'name': notebook.name,
            'description': notebook.description,
            'created_at': notebook.created_at.isoformat(),
            'updated_at': notebook.updated_at.isoformat(),
            'total_cells': len(notebook.cells),
            'code_cells': len(code_cells),
            'markdown_cells': len(markdown_cells),
            'raw_cells': len(raw_cells),
            'executed_code_cells': len([c for c in code_cells if c.executed_at]),
            'total_execution_time': total_execution_time,
            'latest_execution': max((c.executed_at for c in code_cells if c.executed_at), default=None)
        }
    
    def suggest_next_cell(self, notebook_id: str) -> List[Dict[str, str]]:
        """
        基于笔记本内容建议下一个单元格
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            建议的单元格列表
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return []
        
        suggestions = []
        
        # 分析最后几个单元格以提供建议
        last_cells = notebook.cells[-3:] if len(notebook.cells) >= 3 else notebook.cells
        
        for cell in reversed(last_cells):
            if cell.cell_type == 'code':
                # 如果最后的代码单元格涉及数据处理，建议可视化
                content_lower = cell.content.lower()
                if any(kw in content_lower for kw in ['pandas', 'dataframe', 'df.', 'csv', 'dataset']):
                    suggestions.append({
                        'type': 'code',
                        'content': '# Visualize the data\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\n# Create plots based on your data',
                        'reason': 'Detected data processing, suggesting visualization'
                    })
                    break
        
        # 如果笔记本主要是代码，建议添加解释性markdown
        code_ratio = len([c for c in notebook.cells if c.cell_type == 'code']) / len(notebook.cells) if notebook.cells else 0
        if code_ratio > 0.7:
            suggestions.append({
                'type': 'markdown',
                'content': '# Explanation\n\nAdd explanation of what the above code does.',
                'reason': 'High ratio of code cells, suggesting documentation'
            })
        
        return suggestions
    
    def refactor_code_cell(self, 
                          notebook_id: str, 
                          cell_id: str, 
                          refactoring_type: str = "simplify") -> Optional[str]:
        """
        重构代码单元格
        
        Args:
            notebook_id: 笔记本ID
            cell_id: 单元格ID
            refactoring_type: 重构类型
            
        Returns:
            重构后的代码或None
        """
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return None
        
        cell = None
        for c in notebook.cells:
            if c.id == cell_id and c.cell_type == 'code':
                cell = c
                break
        
        if not cell:
            return None
        
        if refactoring_type == "simplify":
            # 使用代码分析器来分析代码
            analysis = self.code_analyzer.analyze_code(cell.content)
            
            # 基于分析结果提供建议
            suggestions = self.code_analyzer.generate_refactoring_suggestions(analysis)
            
            # 返回重构建议而不是自动重构（因为自动重构很复杂）
            refactored_code = cell.content + f"\n\n# Refactoring suggestions:\n"
            for suggestion in suggestions[:3]:  # 只显示前3个建议
                refactored_code += f"# - {suggestion}\n"
            
            # 更新单元格
            cell.content = refactored_code
            notebook.updated_at = datetime.now()
            
            return refactored_code
        
        return None


# 高级功能：智能代码生成助手
class VibecodingAssistant:
    """Vibecoding智能助手"""
    
    def __init__(self, notebook_interface: VibecodingNotebookInterface):
        """
        初始化智能助手
        
        Args:
            notebook_interface: 笔记本接口实例
        """
        self.interface = notebook_interface
        self.generator = CodeGenerator()
    
    def assist_with_task(self, 
                        notebook_id: str, 
                        task_description: str, 
                        context_cells_before: int = 2) -> str:
        """
        协助完成任务
        
        Args:
            notebook_id: 笔记本ID
            task_description: 任务描述
            context_cells_before: 需要考虑的前置单元格数量
            
        Returns:
            生成的代码单元格ID
        """
        # 获取上下文
        notebook = self.interface.get_notebook(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook not found: {notebook_id}")
        
        # 获取最近的几个单元格作为上下文
        context = ""
        start_idx = max(0, len(notebook.cells) - context_cells_before)
        for cell in notebook.cells[start_idx:]:
            context += f"[{cell.cell_type}] {cell.content}\n\n"
        
        # 结合任务描述和上下文生成代码
        full_prompt = f"Context:\n{context}\n\nTask: {task_description}"
        
        # 使用生成器创建代码
        generated = self.generator.generate_code(task_description, context={"previous_code": context})
        
        # 添加到笔记本
        cell_id = self.interface.add_cell(notebook_id, 'code', generated.code)
        
        logger.info(f"Assistant generated code for task: {task_description}")
        return cell_id
    
    def optimize_performance(self, notebook_id: str) -> List[str]:
        """
        优化笔记本性能
        
        Args:
            notebook_id: 笔记本ID
            
        Returns:
            优化建议列表
        """
        notebook = self.interface.get_notebook(notebook_id)
        if not notebook:
            return []
        
        suggestions = []
        
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                analysis = self.interface.code_analyzer.analyze_code(cell.content)
                
                # 检查复杂函数
                complex_functions = [f for f in analysis.functions if f.complexity > 10]
                if complex_functions:
                    suggestions.append(
                        f"Cell {cell.id}: Functions {', '.join(f.name for f in complex_functions)} "
                        f"have high complexity ({max(f.complexity for f in complex_functions)}), "
                        f"consider refactoring"
                    )
                
                # 检查长函数
                long_functions = [f for f in analysis.functions if (f.end_line - f.start_line + 1) > 50]
                if long_functions:
                    suggestions.append(
                        f"Cell {cell.id}: Functions {', '.join(f.name for f in long_functions)} "
                        f"are too long, consider splitting"
                    )
        
        return suggestions


# 示例使用
async def example_usage():
    """示例用法"""
    print("=== Vibecoding笔记本示例 ===")
    
    # 创建笔记本接口
    interface = VibecodingNotebookInterface()
    
    # 创建笔记本
    notebook_id = interface.create_notebook("数据分析示例", "演示Vibecoding功能")
    
    # 添加代码单元格
    interface.add_cell(notebook_id, "markdown", "# 数据分析项目\n\n这是一个使用Vibecoding的例子。")
    
    interface.add_cell(notebook_id, "code", '''
import pandas as pd
import numpy as np

# 创建示例数据
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, 30, 35, 28],
    'salary': [50000, 60000, 70000, 55000]
}
df = pd.DataFrame(data)
print("数据预览:")
print(df.head())
    ''')
    
    interface.add_cell(notebook_id, "code", '''
# 计算平均薪资
avg_salary = df['salary'].mean()
print(f"平均薪资: {avg_salary}")

# 按年龄分组
age_groups = df.groupby(df['age'] // 10 * 10)['salary'].mean()
print("各年龄段平均薪资:")
print(age_groups)
    ''')
    
    # 创建智能助手
    assistant = VibecodingAssistant(interface)
    
    # 让助手添加可视化代码
    visualization_cell_id = assistant.assist_with_task(
        notebook_id,
        "创建一个柱状图显示每个人的薪资"
    )
    
    # 执行笔记本
    print(f"\\n执行笔记本...")
    execution_results = await interface.execute_notebook(notebook_id)
    print(f"执行结果: {execution_results['successful_executions']}/{execution_results['executed_cells']} 成功")
    
    # 获取笔记本摘要
    summary = interface.get_notebook_summary(notebook_id)
    print(f"\\n笔记本摘要: {summary}")
    
    # 获取变量
    variables = interface.get_notebook_variables(notebook_id)
    print(f"\\n笔记本变量: {list(variables.keys())}")
    
    # 保存笔记本
    interface.save_notebook(notebook_id, "example_notebook.ipynb")
    print(f"\\n笔记本已保存到 example_notebook.ipynb")
    
    # 获取重构建议
    optimization_suggestions = assistant.optimize_performance(notebook_id)
    print(f"\\n性能优化建议: {optimization_suggestions}")


if __name__ == "__main__":
    asyncio.run(example_usage())