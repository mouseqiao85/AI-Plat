"""
代码分析器
自动分析代码结构、逻辑和质量
"""

import ast
import astor
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import inspect
import importlib
import os
import sys
from pathlib import Path
import logging
import tokenize
import io

logger = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    """代码问题数据类"""
    type: str  # error, warning, info
    line: int
    column: int
    message: str
    severity: str  # high, medium, low


@dataclass
class FunctionInfo:
    """函数信息数据类"""
    name: str
    start_line: int
    end_line: int
    parameters: List[str]
    return_annotation: Optional[str]
    docstring: Optional[str]
    complexity: int  # 圈复杂度
    called_functions: List[str]


@dataclass
class ClassInfo:
    """类信息数据类"""
    name: str
    start_line: int
    end_line: int
    methods: List[FunctionInfo]
    base_classes: List[str]
    docstring: Optional[str]


@dataclass
class ModuleInfo:
    """模块信息数据类"""
    file_path: str
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]
    variables: List[str]
    issues: List[CodeIssue]


class CodeAnalyzer:
    """代码分析器类"""
    
    def __init__(self):
        """初始化代码分析器"""
        self.issues = []
        self.current_file = ""
        logger.info("Code Analyzer initialized")
    
    def analyze_code(self, code: str, file_path: str = "") -> ModuleInfo:
        """
        分析代码
        
        Args:
            code: 代码字符串
            file_path: 文件路径
            
        Returns:
            模块信息
        """
        self.current_file = file_path
        self.issues = []
        
        try:
            # 解析AST
            tree = ast.parse(code)
            
            # 提取信息
            functions = self._extract_functions(tree)
            classes = self._extract_classes(tree)
            imports = self._extract_imports(tree)
            variables = self._extract_variables(tree)
            
            # 检查代码质量问题
            self._check_code_quality(tree, code.split('\n'))
            
            module_info = ModuleInfo(
                file_path=file_path,
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                issues=self.issues
            )
            
            logger.info(f"Analyzed code in {file_path} with {len(functions)} functions and {len(classes)} classes")
            return module_info
            
        except SyntaxError as e:
            error_issue = CodeIssue(
                type="error",
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Syntax Error: {e.msg}",
                severity="high"
            )
            self.issues.append(error_issue)
            
            return ModuleInfo(
                file_path=file_path,
                functions=[],
                classes=[],
                imports=[],
                variables=[],
                issues=self.issues
            )
    
    def analyze_file(self, file_path: str) -> ModuleInfo:
        """
        分析文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块信息
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        return self.analyze_code(code, file_path)
    
    def _extract_functions(self, tree: ast.AST) -> List[FunctionInfo]:
        """提取函数信息"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 计算圈复杂度
                complexity = self._calculate_cyclomatic_complexity(node)
                
                # 提取参数
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                
                # 提取返回类型注解
                return_annotation = None
                if node.returns:
                    return_annotation = ast.unparse(node.returns)
                
                # 提取文档字符串
                docstring = ast.get_docstring(node)
                
                # 提取被调用的函数
                called_functions = self._extract_called_functions(node)
                
                func_info = FunctionInfo(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    parameters=args,
                    return_annotation=return_annotation,
                    docstring=docstring,
                    complexity=complexity,
                    called_functions=called_functions
                )
                
                functions.append(func_info)
        
        return functions
    
    def _extract_classes(self, tree: ast.AST) -> List[ClassInfo]:
        """提取类信息"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 提取基类
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_classes.append(ast.unparse(base))
                
                # 提取方法
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_info = self._extract_single_method(item)
                        methods.append(method_info)
                
                # 提取文档字符串
                docstring = ast.get_docstring(node)
                
                class_info = ClassInfo(
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    methods=methods,
                    base_classes=base_classes,
                    docstring=docstring
                )
                
                classes.append(class_info)
        
        return classes
    
    def _extract_single_method(self, node: ast.FunctionDef) -> FunctionInfo:
        """提取单个方法信息"""
        complexity = self._calculate_cyclomatic_complexity(node)
        
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)
        
        docstring = ast.get_docstring(node)
        called_functions = self._extract_called_functions(node)
        
        return FunctionInfo(
            name=node.name,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            parameters=args,
            return_annotation=return_annotation,
            docstring=docstring,
            complexity=complexity,
            called_functions=called_functions
        )
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入信息"""
        imports = []
        
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        return imports
    
    def _extract_variables(self, tree: ast.AST) -> List[str]:
        """提取变量信息"""
        variables = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.add(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    variables.add(node.target.id)
        
        return list(variables)
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.BoolOp,)):  # and, or
                complexity += len([n for n in ast.walk(child) if isinstance(n, (ast.And, ast.Or))])
        
        return complexity
    
    def _extract_called_functions(self, node: ast.AST) -> List[str]:
        """提取被调用的函数"""
        called_functions = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    called_functions.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    called_functions.append(ast.unparse(child.func))
        
        return called_functions
    
    def _check_code_quality(self, tree: ast.AST, lines: List[str]):
        """检查代码质量问题"""
        # 检查长函数
        self._check_long_functions(tree)
        
        # 检查复杂的函数
        self._check_complex_functions(tree)
        
        # 检查未使用的导入
        self._check_unused_imports(tree, lines)
        
        # 检查命名规范
        self._check_naming_conventions(tree)
        
        # 检查PEP 8风格问题
        self._check_pep8_issues(lines)
    
    def _check_long_functions(self, tree: ast.AST):
        """检查过长的函数"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, 'end_lineno', node.lineno)
                length = end_line - node.lineno + 1
                
                if length > 50:  # 超过50行认为过长
                    issue = CodeIssue(
                        type="warning",
                        line=node.lineno,
                        column=0,
                        message=f"Function '{node.name}' is too long ({length} lines, recommend < 50)",
                        severity="medium"
                    )
                    self.issues.append(issue)
    
    def _check_complex_functions(self, tree: ast.AST):
        """检查过于复杂的函数"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                
                if complexity > 10:  # 复杂度超过10认为过高
                    issue = CodeIssue(
                        type="warning",
                        line=node.lineno,
                        column=0,
                        message=f"Function '{node.name}' is too complex (complexity: {complexity}, recommend < 10)",
                        severity="medium"
                    )
                    self.issues.append(issue)
    
    def _check_unused_imports(self, tree: ast.AST, lines: List[str]):
        """检查未使用的导入"""
        imports = {}
        
        # 收集导入
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = (node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.asname or alias.name
                    full_name = f"{module}.{alias.name}"
                    imports[name] = (node.lineno, full_name)
        
        # 检查使用情况
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # 检查属性访问
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # 标记未使用的导入
        for name, (line, full_name) in imports.items():
            if name not in used_names:
                issue = CodeIssue(
                    type="warning",
                    line=line,
                    column=0,
                    message=f"Import '{full_name}' is not used",
                    severity="low"
                )
                self.issues.append(issue)
    
    def _check_naming_conventions(self, tree: ast.AST):
        """检查命名规范"""
        for node in ast.walk(tree):
            name = None
            line = 0
            
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                line = node.lineno
            elif isinstance(node, ast.ClassDef):
                name = node.name
                line = node.lineno
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
                name = node.id
                line = node.lineno
            
            if name:
                # 检查类名是否遵循PascalCase
                if isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
                        issue = CodeIssue(
                            type="warning",
                            line=line,
                            column=0,
                            message=f"Class name '{name}' should use PascalCase",
                            severity="low"
                        )
                        self.issues.append(issue)
                
                # 检查函数和变量名是否遵循snake_case
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or \
                     (isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param))):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', name):
                        issue = CodeIssue(
                            type="warning",
                            line=line,
                            column=0,
                            message=f"Function/variable name '{name}' should use snake_case",
                            severity="low"
                        )
                        self.issues.append(issue)
    
    def _check_pep8_issues(self, lines: List[str]):
        """检查PEP 8风格问题"""
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # 检查行长度（超过79字符）
            if len(line) > 79:
                issue = CodeIssue(
                    type="info",
                    line=line_num,
                    column=79,
                    message=f"Line too long ({len(line)} > 79 characters)",
                    severity="low"
                )
                self.issues.append(issue)
            
            # 检查行尾空白
            if line.rstrip() != line:
                issue = CodeIssue(
                    type="warning",
                    line=line_num,
                    column=len(line.rstrip()),
                    message="Trailing whitespace",
                    severity="low"
                )
                self.issues.append(issue)
    
    def generate_refactoring_suggestions(self, module_info: ModuleInfo) -> List[str]:
        """
        生成重构建议
        
        Args:
            module_info: 模块信息
            
        Returns:
            重构建议列表
        """
        suggestions = []
        
        # 针对复杂函数的建议
        complex_functions = [f for f in module_info.functions if f.complexity > 8]
        if complex_functions:
            suggestions.append(
                f"Found {len(complex_functions)} complex functions that should be simplified:"
            )
            for func in complex_functions:
                suggestions.append(f"  - {func.name} (complexity: {func.complexity})")
        
        # 针对长函数的建议
        long_functions = [f for f in module_info.functions if (f.end_line - f.start_line + 1) > 30]
        if long_functions:
            suggestions.append(
                f"Found {len(long_functions)} long functions that should be split:"
            )
            for func in long_functions:
                length = func.end_line - func.start_line + 1
                suggestions.append(f"  - {func.name} ({length} lines)")
        
        # 针对未使用导入的建议
        unused_import_issues = [issue for issue in module_info.issues if "not used" in issue.message]
        if unused_import_issues:
            suggestions.append(f"Found {len(unused_import_issues)} unused imports to remove")
        
        # 针对命名规范的建议
        naming_issues = [issue for issue in module_info.issues if "should use" in issue.message]
        if naming_issues:
            suggestions.append(f"Found {len(naming_issues)} naming convention issues to fix")
        
        return suggestions
    
    def get_code_summary(self, module_info: ModuleInfo) -> Dict[str, Any]:
        """
        获取代码摘要
        
        Args:
            module_info: 模块信息
            
        Returns:
            代码摘要
        """
        total_functions = len(module_info.functions)
        total_classes = len(module_info.classes)
        total_lines = 0
        
        # 估算代码行数
        if module_info.file_path and os.path.exists(module_info.file_path):
            with open(module_info.file_path, 'r', encoding='utf-8') as f:
                total_lines = len(f.readlines())
        
        avg_complexity = 0
        if module_info.functions:
            avg_complexity = sum(f.complexity for f in module_info.functions) / len(module_info.functions)
        
        return {
            'file_path': module_info.file_path,
            'total_functions': total_functions,
            'total_classes': total_classes,
            'total_imports': len(module_info.imports),
            'total_variables': len(module_info.variables),
            'total_lines': total_lines,
            'total_issues': len(module_info.issues),
            'avg_function_complexity': round(avg_complexity, 2),
            'max_function_complexity': max((f.complexity for f in module_info.functions), default=0),
            'issue_breakdown': {
                'errors': len([i for i in module_info.issues if i.type == 'error']),
                'warnings': len([i for i in module_info.issues if i.type == 'warning']),
                'infos': len([i for i in module_info.issues if i.type == 'info'])
            }
        }


# 示例使用
if __name__ == "__main__":
    # 创建代码分析器
    analyzer = CodeAnalyzer()
    
    # 示例代码
    sample_code = '''
"""这是一个示例模块"""

import os
import sys
from typing import List, Dict, Optional

class DataProcessor:
    """数据处理类"""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self.data = []
    
    def process_data(self, raw_data: List[Dict]) -> List[Dict]:
        """处理原始数据"""
        processed = []
        for item in raw_data:
            if item.get("valid", True):
                processed.append({
                    "id": item.get("id"),
                    "value": item.get("value", 0) * 2
                })
            else:
                continue
        return processed
    
    def save_to_file(self, data: List[Dict], filename: str):
        """保存到文件"""
        with open(filename, 'w') as f:
            for item in data:
                f.write(str(item) + "\\n")

def analyze_dataset(dataset: List[Dict]) -> Dict[str, any]:
    """分析数据集"""
    stats = {
        "total": len(dataset),
        "has_values": sum(1 for d in dataset if d.get("value")),
        "avg_value": sum(d.get("value", 0) for d in dataset) / len(dataset) if dataset else 0
    }
    return stats

def complex_function(x, y, z):
    """一个复杂的函数示例"""
    if x > 0:
        if y > 0:
            if z > 0:
                result = x + y + z
            else:
                result = x + y - z
        else:
            if z > 0:
                result = x - y + z
            else:
                result = x - y - z
    else:
        if y > 0:
            if z > 0:
                result = -x + y + z
            else:
                result = -x + y - z
        else:
            if z > 0:
                result = -x - y + z
            else:
                result = -x - y - z
    return result
'''
    
    # 分析代码
    module_info = analyzer.analyze_code(sample_code, "sample_module.py")
    
    # 输出结果
    print("=== 代码分析结果 ===")
    summary = analyzer.get_code_summary(module_info)
    print(f"摘要: {summary}")
    
    print(f"\\n函数列表 ({len(module_info.functions)}):")
    for func in module_info.functions:
        print(f"  - {func.name}: {func.complexity} complexity, {func.parameters}")
    
    print(f"\\n类列表 ({len(module_info.classes)}):")
    for cls in module_info.classes:
        print(f"  - {cls.name}: {len(cls.methods)} methods")
    
    print(f"\\n问题列表 ({len(module_info.issues)}):")
    for issue in module_info.issues:
        print(f"  [{issue.severity}] {issue.line}:{issue.column} - {issue.message}")
    
    print("\\n重构建议:")
    suggestions = analyzer.generate_refactoring_suggestions(module_info)
    for suggestion in suggestions:
        print(f"  - {suggestion}")