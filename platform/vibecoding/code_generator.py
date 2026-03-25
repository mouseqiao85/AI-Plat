"""
代码生成器
基于自然语言描述和上下文生成代码
"""

import ast
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import keyword
import random
import string

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    """生成的代码数据类"""
    code: str
    quality_score: float  # 代码质量评分 (0-1)
    potential_issues: List[str]
    dependencies: List[str]


class CodeGenerator:
    """代码生成器类"""
    
    def __init__(self):
        """初始化代码生成器"""
        self.known_patterns = self._initialize_patterns()
        self.common_imports = self._initialize_common_imports()
        logger.info("Code Generator initialized")
    
    def _initialize_patterns(self) -> Dict[str, str]:
        """初始化常见代码模式"""
        return {
            'data_processing': '''
def process_data(input_data):
    """
    处理输入数据
    
    Args:
        input_data: 输入数据
        
    Returns:
        处理后的数据
    """
    result = []
    for item in input_data:
        # 在这里添加处理逻辑
        processed_item = item  # 替换为实际处理逻辑
        result.append(processed_item)
    return result
''',
            'api_endpoint': '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

@app.get("/items/{item_id}")
def get_item(item_id: int):
    # 实现获取项目逻辑
    return {"item_id": item_id}

@app.post("/items/")
def create_item(item: Item):
    # 实现创建项目逻辑
    return item
''',
            'machine_learning_pipeline': '''
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def build_ml_pipeline(data_path: str):
    """
    构建机器学习管道
    
    Args:
        data_path: 数据路径
        
    Returns:
        训练好的模型
    """
    # 加载数据
    df = pd.read_csv(data_path)
    
    # 数据预处理
    X = df.drop('target', axis=1)  # 替换 'target' 为实际目标列名
    y = df['target']
    
    # 分割数据
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 训练模型
    model = RandomForestClassifier(random_state=42)
    model.fit(X_train, y_train)
    
    # 评估模型
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model accuracy: {accuracy:.2f}")
    
    return model
''',
            'data_visualization': '''
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def visualize_data(data, plot_type='histogram'):
    """
    可视化数据
    
    Args:
        data: 要可视化的数据
        plot_type: 图表类型
    """
    plt.figure(figsize=(10, 6))
    
    if plot_type == 'histogram':
        plt.hist(data, bins=30)
        plt.title('Histogram')
    elif plot_type == 'scatter':
        plt.scatter(data[:, 0], data[:, 1])
        plt.title('Scatter Plot')
    elif plot_type == 'boxplot':
        plt.boxplot(data)
        plt.title('Box Plot')
    
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.show()
'''
        }
    
    def _initialize_common_imports(self) -> Dict[str, List[str]]:
        """初始化常见导入"""
        return {
            'data_processing': ['import pandas as pd', 'import numpy as np'],
            'api_development': ['from fastapi import FastAPI', 'from pydantic import BaseModel'],
            'machine_learning': ['import pandas as pd', 'from sklearn.model_selection import train_test_split'],
            'visualization': ['import matplotlib.pyplot as plt', 'import seaborn as sns'],
            'general_utils': ['import os', 'import sys', 'from typing import List, Dict, Optional']
        }
    
    def generate_code(self, 
                     description: str, 
                     context: Optional[Dict[str, Any]] = None,
                     language: str = 'python') -> GeneratedCode:
        """
        根据描述生成代码
        
        Args:
            description: 需求描述
            context: 上下文信息
            language: 目标语言
            
        Returns:
            生成的代码
        """
        if language.lower() != 'python':
            raise ValueError("Currently only Python is supported")
        
        logger.info(f"Generating code for: {description}")
        
        # 分析描述并确定代码类型
        code_type = self._determine_code_type(description)
        
        # 生成代码
        generated_code = self._generate_specific_code(description, code_type, context)
        
        # 分析生成的代码
        quality_score, issues = self._analyze_generated_code(generated_code)
        
        # 确定依赖
        dependencies = self._extract_dependencies(generated_code)
        
        return GeneratedCode(
            code=generated_code,
            quality_score=quality_score,
            potential_issues=issues,
            dependencies=dependencies
        )
    
    def _determine_code_type(self, description: str) -> str:
        """确定代码类型"""
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in ['api', 'endpoint', 'rest', 'web']):
            return 'api_endpoint'
        elif any(keyword in desc_lower for keyword in ['process', 'data', 'clean', 'transform']):
            return 'data_processing'
        elif any(keyword in desc_lower for keyword in ['model', 'train', 'predict', 'ml', 'machine learning']):
            return 'machine_learning_pipeline'
        elif any(keyword in desc_lower for keyword in ['visualize', 'plot', 'chart', 'graph']):
            return 'data_visualization'
        else:
            return 'general'
    
    def _generate_specific_code(self, 
                               description: str, 
                               code_type: str, 
                               context: Optional[Dict[str, Any]]) -> str:
        """生成特定类型的代码"""
        if code_type in self.known_patterns:
            # 基于已知模式生成
            template = self.known_patterns[code_type]
            return self._customize_template(template, description, context)
        else:
            # 通用代码生成
            return self._generate_general_code(description, context)
    
    def _customize_template(self, 
                          template: str, 
                          description: str, 
                          context: Optional[Dict[str, Any]]) -> str:
        """定制代码模板"""
        customized = template
        
        # 根据描述定制
        if 'csv' in description.lower() or 'excel' in description.lower():
            customized = customized.replace(
                'input_data', 
                'data = pd.read_csv(file_path)' if 'pd.read_csv' not in customized else 'input_data'
            )
        
        # 添加适当的导入
        imports = self._get_relevant_imports(description)
        if imports:
            # 检查是否已有导入，避免重复
            existing_imports = [line for line in customized.split('\n') if line.strip().startswith('import')]
            new_imports = [imp for imp in imports if not any(imp.split()[-1] in existing for existing in existing_imports)]
            if new_imports:
                import_section = '\n'.join(new_imports) + '\n'
                customized = import_section + customized
        
        return customized
    
    def _get_relevant_imports(self, description: str) -> List[str]:
        """获取相关导入"""
        desc_lower = description.lower()
        imports = []
        
        if any(kw in desc_lower for kw in ['data', 'pandas', 'csv', 'excel']):
            imports.extend(self.common_imports.get('data_processing', []))
        if any(kw in desc_lower for kw in ['api', 'web', 'endpoint']):
            imports.extend(self.common_imports.get('api_development', []))
        if any(kw in desc_lower for kw in ['model', 'ml', 'sklearn']):
            imports.extend(self.common_imports.get('machine_learning', []))
        if any(kw in desc_lower for kw in ['visualize', 'plot', 'chart']):
            imports.extend(self.common_imports.get('visualization', []))
        
        # 去重
        unique_imports = []
        seen = set()
        for imp in imports:
            if imp not in seen:
                unique_imports.append(imp)
                seen.add(imp)
        
        return unique_imports
    
    def _generate_general_code(self, 
                              description: str, 
                              context: Optional[Dict[str, Any]]) -> str:
        """生成通用代码"""
        # 这里实现更复杂的代码生成逻辑
        # 基于自然语言描述生成代码
        desc_lower = description.lower()
        
        # 确定函数名
        func_name = self._generate_function_name(description)
        
        # 确定参数
        params = self._extract_parameters(description)
        
        # 生成函数体
        func_body = self._generate_function_body(description, params)
        
        # 构建完整函数
        param_str = ", ".join(params) if params else ""
        code = f'def {func_name}({param_str}):\n'
        code += f'    """{description}"""\n'
        code += func_body
        code += '\n'
        
        # 添加必要的导入
        imports = self._get_relevant_imports(description)
        if imports:
            code = '\n'.join(imports) + '\n\n' + code
        
        return code
    
    def _generate_function_name(self, description: str) -> str:
        """生成函数名"""
        # 提取关键词并转换为蛇形命名
        words = re.findall(r'\b\w+\b', description)
        
        # 过滤掉常见词汇
        filtered_words = [w.lower() for w in words 
                         if w.lower() not in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with']]
        
        # 取前几个有意义的词
        meaningful_words = filtered_words[:4] if filtered_words else ['process']
        
        # 转换为蛇形命名
        func_name = '_'.join(meaningful_words)
        
        # 确保不是关键字
        if keyword.iskeyword(func_name):
            func_name += '_func'
        
        # 确保是有效的标识符
        func_name = re.sub(r'[^a-zA-Z0-9_]', '_', func_name)
        
        # 确保以字母开头
        if func_name and not func_name[0].isalpha():
            func_name = 'func_' + func_name
        
        return func_name
    
    def _extract_parameters(self, description: str) -> List[str]:
        """提取参数"""
        params = []
        
        # 简单的参数提取逻辑
        if 'file' in description.lower():
            params.append('file_path: str')
        if 'data' in description.lower():
            params.append('data')
        if 'config' in description.lower():
            params.append('config: dict')
        if 'model' in description.lower():
            params.append('model')
        if 'list' in description.lower() or 'array' in description.lower():
            params.append('items: list')
        
        # 如果没有识别到参数，添加通用参数
        if not params:
            params.append('input_data')
        
        return params
    
    def _generate_function_body(self, description: str, params: List[str]) -> str:
        """生成函数体"""
        desc_lower = description.lower()
        body_lines = []
        
        # 添加文档字符串
        body_lines.append('    """')
        body_lines.append(f'    {description}')
        body_lines.append('    """')
        
        # 根据描述生成相应的代码逻辑
        if 'process' in desc_lower or 'transform' in desc_lower:
            body_lines.append('    # Process the input data')
            body_lines.append('    result = []')
            body_lines.append('    for item in input_data:')  # 假设有一个input_data参数
            body_lines.append('        # Add processing logic here')
            body_lines.append('        processed_item = item')
            body_lines.append('        result.append(processed_item)')
            body_lines.append('    return result')
        elif 'calculate' in desc_lower or 'compute' in desc_lower:
            body_lines.append('    # Calculate the result')
            body_lines.append('    result = 0  # Replace with actual calculation')
            body_lines.append('    return result')
        elif 'filter' in desc_lower or 'select' in desc_lower:
            body_lines.append('    # Filter the data based on criteria')
            body_lines.append('    result = [item for item in input_data if True]  # Replace with actual condition')
            body_lines.append('    return result')
        elif 'save' in desc_lower or 'write' in desc_lower:
            body_lines.append('    # Save data to specified location')
            body_lines.append('    pass  # Implement saving logic')
        else:
            body_lines.append('    # Implement the required functionality')
            body_lines.append('    pass')
        
        return '\n'.join(body_lines)
    
    def _analyze_generated_code(self, code: str) -> Tuple[float, List[str]]:
        """分析生成的代码质量"""
        issues = []
        
        # 检查语法
        try:
            ast.parse(code)
            syntax_valid = True
        except SyntaxError as e:
            syntax_valid = False
            issues.append(f"Syntax error: {str(e)}")
        
        # 检查代码长度
        lines = code.split('\n')
        if len(lines) > 100:
            issues.append(f"Generated code is very long ({len(lines)} lines), consider breaking it down")
        
        # 检查是否有占位符
        if 'TODO' in code or 'FIXME' in code or '# Replace' in code:
            issues.append("Generated code contains placeholders that need to be implemented")
        
        # 计算质量评分
        base_score = 1.0
        if not syntax_valid:
            base_score -= 0.5
        if any('Replace' in line for line in lines):
            base_score -= 0.2
        if len(issues) > 0:
            base_score -= 0.1 * len(issues)
        
        # 确保评分在0-1之间
        quality_score = max(0.0, min(1.0, base_score))
        
        return quality_score, issues
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """提取依赖"""
        dependencies = set()
        
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                # 提取导入的库名
                if line.startswith('import '):
                    lib = line[len('import '):].split()[0]
                    dependencies.add(lib.split('.')[0])  # 只取顶级包名
                elif line.startswith('from '):
                    lib = line[len('from '):].split()[0]
                    dependencies.add(lib.split('.')[0])  # 只取顶级包名
        
        return list(dependencies)
    
    def refine_code(self, 
                   code: str, 
                   feedback: str, 
                   context: Optional[Dict[str, Any]] = None) -> GeneratedCode:
        """
        根据反馈精炼代码
        
        Args:
            code: 原始代码
            feedback: 反馈描述
            context: 上下文信息
            
        Returns:
            精炼后的代码
        """
        logger.info(f"Refining code based on feedback: {feedback}")
        
        # 这里可以实现更复杂的代码精炼逻辑
        # 目前简单地在原代码基础上添加注释
        refined_code = code
        if 'performance' in feedback.lower():
            refined_code = self._optimize_for_performance(code)
        elif 'readability' in feedback.lower():
            refined_code = self._improve_readability(code)
        elif 'bug' in feedback.lower() or 'error' in feedback.lower():
            refined_code = self._fix_bugs(code)
        
        quality_score, issues = self._analyze_generated_code(refined_code)
        dependencies = self._extract_dependencies(refined_code)
        
        return GeneratedCode(
            code=refined_code,
            quality_score=quality_score,
            potential_issues=issues,
            dependencies=dependencies
        )
    
    def _optimize_for_performance(self, code: str) -> str:
        """优化性能"""
        # 简单的性能优化提示
        optimized_code = code
        if 'for item in' in code and 'range(len(' in code:
            # 提示使用更高效的迭代方式
            optimized_code += "\n    # TODO: Consider using vectorized operations or list comprehensions for better performance\n"
        return optimized_code
    
    def _improve_readability(self, code: str) -> str:
        """提高可读性"""
        # 添加更多注释和改进变量命名
        improved_code = code
        improved_code += "\n    # TODO: Add more descriptive variable names and additional comments for clarity\n"
        return improved_code
    
    def _fix_bugs(self, code: str) -> str:
        """修复错误"""
        # 简单的错误修复提示
        fixed_code = code
        fixed_code += "\n    # TODO: Review and fix potential bugs identified in the feedback\n"
        return fixed_code
    
    def generate_class(self, 
                      class_description: str, 
                      attributes: List[Dict[str, str]], 
                      methods: List[Dict[str, str]]) -> GeneratedCode:
        """
        生成类代码
        
        Args:
            class_description: 类描述
            attributes: 属性列表
            methods: 方法列表
            
        Returns:
            生成的类代码
        """
        class_name = self._generate_class_name(class_description)
        
        # 生成类定义
        class_code = f'class {class_name}:\n'
        class_code += f'    """{class_description}"""\n\n'
        
        # 添加属性
        if attributes:
            # 生成__init__方法
            init_params = [f"{attr['name']}: {attr.get('type', 'Any')} = {attr.get('default', 'None')}" 
                          for attr in attributes]
            init_param_names = [attr['name'] for attr in attributes]
            
            class_code += '    def __init__(self, ' + ', '.join(init_params) + '):\n'
            for param_name in init_param_names:
                class_code += f'        self.{param_name} = {param_name}\n'
            class_code += '\n'
        
        # 添加方法
        for method in methods:
            method_name = method.get('name', 'method_name')
            method_desc = method.get('description', 'Method description')
            method_params = method.get('parameters', [])
            
            param_str = ', '.join([f"{p['name']}: {p.get('type', 'Any')} = {p.get('default', 'None')}" 
                                 for p in method_params])
            
            class_code += f'    def {method_name}(self, {param_str}):\n'
            class_code += f'        """{method_desc}"""\n'
            class_code += '        # Implement method logic here\n'
            class_code += '        pass\n\n'
        
        # 分析生成的代码
        quality_score, issues = self._analyze_generated_code(class_code)
        dependencies = self._extract_dependencies(class_code)
        
        return GeneratedCode(
            code=class_code,
            quality_score=quality_score,
            potential_issues=issues,
            dependencies=dependencies
        )
    
    def _generate_class_name(self, description: str) -> str:
        """生成类名"""
        # 提取描述中的名词短语并转换为帕斯卡命名
        words = re.findall(r'\b[A-Za-z]+\b', description)
        
        # 过滤掉常见词汇
        filtered_words = [w for w in words 
                         if w.lower() not in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with']]
        
        # 取前几个有意义的词并首字母大写
        meaningful_words = [w.capitalize() for w in filtered_words[:3]] if filtered_words else ['Generic']
        
        # 组合成类名
        class_name = ''.join(meaningful_words)
        
        # 确保是有效的标识符
        class_name = re.sub(r'[^a-zA-Z0-9_]', '', class_name)
        
        # 确保以字母开头
        if class_name and not class_name[0].isalpha():
            class_name = 'Class' + class_name
        
        return class_name


# 示例使用
if __name__ == "__main__":
    # 创建代码生成器
    generator = CodeGenerator()
    
    # 示例1: 生成数据处理函数
    print("=== 示例1: 数据处理函数 ===")
    description1 = "创建一个函数来处理CSV文件中的销售数据，计算每种产品的总销售额"
    generated1 = generator.generate_code(description1)
    print(f"生成的代码:\\n{generated1.code}")
    print(f"质量评分: {generated1.quality_score}")
    print(f"潜在问题: {generated1.potential_issues}")
    print(f"依赖: {generated1.dependencies}")
    
    # 示例2: 生成API端点
    print("\\n=== 示例2: API端点 ===")
    description2 = "创建一个FastAPI端点来获取用户信息"
    generated2 = generator.generate_code(description2)
    print(f"生成的代码:\\n{generated2.code}")
    
    # 示例3: 生成类
    print("\\n=== 示例3: 生成类 ===")
    class_desc = "用户管理类，用于处理用户注册、登录和信息更新"
    attributes = [
        {'name': 'username', 'type': 'str'},
        {'name': 'email', 'type': 'str'},
        {'name': 'password_hash', 'type': 'str'}
    ]
    methods = [
        {
            'name': 'register',
            'description': '注册新用户',
            'parameters': [{'name': 'username', 'type': 'str'}, {'name': 'password', 'type': 'str'}]
        },
        {
            'name': 'login',
            'description': '用户登录',
            'parameters': [{'name': 'username', 'type': 'str'}, {'name': 'password', 'type': 'str'}]
        }
    ]
    generated_class = generator.generate_class(class_desc, attributes, methods)
    print(f"生成的类:\\n{generated_class.code}")