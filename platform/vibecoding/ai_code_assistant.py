"""
AI Code Assistant - Enhanced Vibecoding Module
借鉴opencode能力实现的AI代码助手

Features:
- Natural language to code generation
- Code explanation and documentation
- Smart refactoring suggestions
- Error detection and fixes
- Multi-file project understanding
- Code completion
"""

import os
import re
import ast
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    JAVA = "java"
    RUST = "rust"


class TaskType(Enum):
    GENERATE = "generate"
    EXPLAIN = "explain"
    REFACTOR = "refactor"
    DEBUG = "debug"
    DOCUMENT = "document"
    COMPLETE = "complete"
    REVIEW = "review"


@dataclass
class CodeContext:
    """Code context for analysis"""
    file_path: str = ""
    language: CodeLanguage = CodeLanguage.PYTHON
    surrounding_code: str = ""
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)


@dataclass
class CodeSuggestion:
    """Code suggestion result"""
    code: str
    explanation: str
    confidence: float
    task_type: TaskType
    issues: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)


@dataclass
class ProjectFile:
    """Project file representation"""
    path: str
    content: str
    language: CodeLanguage
    summary: str
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


class AICodeAssistant:
    """
    AI Code Assistant - Main class for enhanced coding capabilities
    借鉴opencode的能力模式
    """
    
    def __init__(self, model_config: Dict[str, Any] = None):
        self.model_config = model_config or {}
        self.conversation_history: List[Dict] = []
        self.project_files: Dict[str, ProjectFile] = {}
        self.code_patterns = self._initialize_patterns()
        self.refactoring_rules = self._initialize_refactoring_rules()
        self.debugging_patterns = self._initialize_debug_patterns()
        
    def _initialize_patterns(self) -> Dict[str, Any]:
        """Initialize code patterns for different tasks"""
        return {
            "api_endpoints": {
                "patterns": ["@app.route", "@app.get", "@app.post", "def get_", "def post_", "def put_", "def delete_"],
                "template": '''@router.{method}("/{path}")
async def {function_name}({params}):
    """
    {description}
    
    Returns:
        {return_type}: {return_description}
    """
    # Implementation
    return {{"success": True, "data": None}}
''',
            },
            "data_models": {
                "patterns": ["class ", "BaseModel", "@dataclass", "TypedDict"],
                "template": '''class {ClassName}(BaseModel):
    """
    {description}
    """
    {fields}
    
    class Config:
        from_attributes = True
''',
            },
            "services": {
                "patterns": ["class.*Service", "def process", "def handle", "async def"],
                "template": '''class {ServiceName}:
    """
    {description}
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {{}}
    
    async def execute(self, *args, **kwargs):
        """Execute the service logic"""
        # Implementation
        pass
''',
            },
            "tests": {
                "patterns": ["def test_", "assert", "pytest", "@pytest"],
                "template": '''def test_{function_name}():
    """
    Test {description}
    """
    # Arrange
    input_data = {{}}
    expected = {{}}
    
    # Act
    result = {function_under_test}(input_data)
    
    # Assert
    assert result == expected
''',
            },
            "crud_operations": {
                "patterns": ["create", "read", "update", "delete", "get", "list", "save"],
                "template": '''async def {operation}_{entity}({params}):
    """
    {description}
    """
    async with get_session() as session:
        # Implementation
        pass
    return result
''',
            },
        }
    
    def _initialize_refactoring_rules(self) -> List[Dict[str, Any]]:
        """Initialize refactoring rules"""
        return [
            {
                "name": "extract_function",
                "pattern": "long_function",
                "description": "Extract repeated code into a separate function",
                "priority": 1,
            },
            {
                "name": "simplify_conditionals",
                "pattern": "nested_if",
                "description": "Simplify nested if statements",
                "priority": 2,
            },
            {
                "name": "remove_duplicate_code",
                "pattern": "duplicate",
                "description": "Remove duplicate code blocks",
                "priority": 1,
            },
            {
                "name": "add_type_hints",
                "pattern": "missing_types",
                "description": "Add type hints to function parameters and returns",
                "priority": 3,
            },
            {
                "name": "improve_naming",
                "pattern": "bad_naming",
                "description": "Improve variable and function names",
                "priority": 2,
            },
            {
                "name": "add_docstrings",
                "pattern": "missing_docs",
                "description": "Add docstrings to functions and classes",
                "priority": 3,
            },
        ]
    
    def _initialize_debug_patterns(self) -> Dict[str, List[str]]:
        """Initialize common debugging patterns"""
        return {
            "null_pointer": ["None", "null", "undefined", "NullPointerException"],
            "type_error": ["TypeError", "type mismatch", "cannot convert"],
            "index_error": ["IndexError", "list index out of range", "KeyError"],
            "syntax_error": ["SyntaxError", "invalid syntax", "unexpected token"],
            "import_error": ["ImportError", "ModuleNotFoundError", "No module named"],
            "connection_error": ["ConnectionError", "ConnectionRefused", "timeout"],
        }
    
    def process_instruction(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """
        Process a natural language instruction and generate code suggestion
        
        Args:
            instruction: Natural language instruction
            context: Code context for the instruction
            
        Returns:
            CodeSuggestion with generated code and explanation
        """
        task_type = self._detect_task_type(instruction)
        
        if task_type == TaskType.GENERATE:
            return self._handle_generation(instruction, context)
        elif task_type == TaskType.EXPLAIN:
            return self._handle_explanation(instruction, context)
        elif task_type == TaskType.REFACTOR:
            return self._handle_refactoring(instruction, context)
        elif task_type == TaskType.DEBUG:
            return self._handle_debugging(instruction, context)
        elif task_type == TaskType.DOCUMENT:
            return self._handle_documentation(instruction, context)
        elif task_type == TaskType.COMPLETE:
            return self._handle_completion(instruction, context)
        elif task_type == TaskType.REVIEW:
            return self._handle_review(instruction, context)
        else:
            return self._handle_generation(instruction, context)
    
    def _detect_task_type(self, instruction: str) -> TaskType:
        """Detect the type of task from the instruction"""
        instruction_lower = instruction.lower()
        
        if any(kw in instruction_lower for kw in ["create", "generate", "write", "implement", "build"]):
            return TaskType.GENERATE
        elif any(kw in instruction_lower for kw in ["explain", "what does", "how does", "describe"]):
            return TaskType.EXPLAIN
        elif any(kw in instruction_lower for kw in ["refactor", "improve", "optimize", "clean"]):
            return TaskType.REFACTOR
        elif any(kw in instruction_lower for kw in ["fix", "debug", "error", "bug", "issue"]):
            return TaskType.DEBUG
        elif any(kw in instruction_lower for kw in ["document", "add doc", "comment", "docstring"]):
            return TaskType.DOCUMENT
        elif any(kw in instruction_lower for kw in ["complete", "finish", "continue"]):
            return TaskType.COMPLETE
        elif any(kw in instruction_lower for kw in ["review", "check", "analyze", "audit"]):
            return TaskType.REVIEW
        else:
            return TaskType.GENERATE
    
    def _handle_generation(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle code generation tasks"""
        code_type = self._detect_code_type(instruction)
        
        if code_type == "api_endpoint":
            code, explanation = self._generate_api_endpoint(instruction, context)
        elif code_type == "data_model":
            code, explanation = self._generate_data_model(instruction, context)
        elif code_type == "service":
            code, explanation = self._generate_service(instruction, context)
        elif code_type == "test":
            code, explanation = self._generate_test(instruction, context)
        elif code_type == "crud":
            code, explanation = self._generate_crud(instruction, context)
        else:
            code, explanation = self._generate_general_code(instruction, context)
        
        issues = self._detect_issues(code)
        improvements = self._suggest_improvements(code)
        
        return CodeSuggestion(
            code=code,
            explanation=explanation,
            confidence=0.85,
            task_type=TaskType.GENERATE,
            issues=issues,
            improvements=improvements,
        )
    
    def _detect_code_type(self, instruction: str) -> str:
        """Detect the type of code to generate"""
        instruction_lower = instruction.lower()
        
        if any(kw in instruction_lower for kw in ["api", "endpoint", "route", "rest", "get", "post", "put", "delete"]):
            return "api_endpoint"
        elif any(kw in instruction_lower for kw in ["model", "schema", "dataclass", "entity", "dto"]):
            return "data_model"
        elif any(kw in instruction_lower for kw in ["service", "handler", "processor", "manager"]):
            return "service"
        elif any(kw in instruction_lower for kw in ["test", "spec", "unittest", "pytest"]):
            return "test"
        elif any(kw in instruction_lower for kw in ["crud", "create", "read", "update", "delete", "repository"]):
            return "crud"
        else:
            return "general"
    
    def _generate_api_endpoint(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate API endpoint code"""
        method = "get"
        for m in ["post", "put", "delete", "patch", "get"]:
            if m in instruction.lower():
                method = m
                break
        
        path = self._extract_path(instruction)
        function_name = self._generate_function_name(instruction)
        description = self._extract_description(instruction)
        
        code = f'''@router.{method}("/{path}")
async def {function_name}():
    """
    {description}
    
    Returns:
        dict: Response data
    """
    try:
        # TODO: Implement the logic
        result = {{"success": True, "data": None}}
        return result
    except Exception as e:
        logger.error(f"Error in {function_name}: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))
'''
        
        explanation = f"Generated a {method.upper()} endpoint for '{path}'. This endpoint {description.lower()}. Add your business logic in the try block."
        
        return code, explanation
    
    def _generate_data_model(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate data model code"""
        class_name = self._extract_class_name(instruction)
        fields = self._extract_fields(instruction)
        
        fields_str = "\n    ".join([f'{name}: {type_}' for name, type_ in fields])
        
        code = f'''from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class {class_name}(BaseModel):
    """
    {class_name} data model
    """
    {fields_str}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
'''
        
        explanation = f"Generated a Pydantic model for {class_name}. The model includes fields: {', '.join([f[0] for f in fields])}. Add validation as needed."
        
        return code, explanation
    
    def _generate_service(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate service code"""
        service_name = self._extract_class_name(instruction)
        description = self._extract_description(instruction)
        
        code = f'''from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class {service_name}:
    """
    {description}
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service"""
        if self._initialized:
            return
        # Add initialization logic here
        self._initialized = True
        logger.info(f"{service_name} initialized")
    
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the main service logic
        
        Returns:
            Dict containing the result
        """
        await self.initialize()
        
        try:
            # TODO: Implement service logic
            result = {{"success": True}}
            return result
        except Exception as e:
            logger.error(f"Error executing {service_name}: {{e}}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        logger.info(f"{service_name} cleaned up")
'''
        
        explanation = f"Generated a service class {service_name}. The service includes initialize, execute, and cleanup methods for lifecycle management."
        
        return code, explanation
    
    def _generate_test(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate test code"""
        test_name = self._generate_function_name(instruction)
        description = self._extract_description(instruction)
        
        code = f'''import pytest
from unittest.mock import Mock, patch, AsyncMock

class Test{test_name.title().replace('_', '')}:
    """Tests for {description}"""
    
    @pytest.fixture
    def setup(self):
        """Setup test fixtures"""
        return {{}}
    
    @pytest.mark.asyncio
    async def test_{test_name}_success(self, setup):
        """Test successful execution"""
        # Arrange
        input_data = {{}}
        expected = {{}}
        
        # Act
        # result = await function_under_test(input_data)
        
        # Assert
        # assert result == expected
        pass
    
    @pytest.mark.asyncio
    async def test_{test_name}_error_handling(self, setup):
        """Test error handling"""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        # with pytest.raises(ValueError):
        #     await function_under_test(invalid_input)
        pass
'''
        
        explanation = f"Generated test cases for {description}. Includes success and error handling test templates. Implement the actual test logic based on your requirements."
        
        return code, explanation
    
    def _generate_crud(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate CRUD operations code"""
        entity = self._extract_entity_name(instruction)
        class_name = entity.capitalize()
        
        code = f'''from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class {class_name}Repository:
    """Repository for {entity} CRUD operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: dict) -> {class_name}:
        """Create a new {entity}"""
        entity = {class_name}(**data)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, id: int) -> Optional[{class_name}]:
        """Get {entity} by ID"""
        result = await self.session.execute(
            select({class_name}).where({class_name}.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[{class_name}]:
        """Get all {entity}s with pagination"""
        result = await self.session.execute(
            select({class_name}).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, id: int, data: dict) -> Optional[{class_name}]:
        """Update {entity} by ID"""
        entity = await self.get_by_id(id)
        if not entity:
            return None
        for key, value in data.items():
            setattr(entity, key, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, id: int) -> bool:
        """Delete {entity} by ID"""
        entity = await self.get_by_id(id)
        if not entity:
            return False
        await self.session.delete(entity)
        await self.session.commit()
        return True
'''
        
        explanation = f"Generated CRUD repository for {entity}. Includes create, read, update, and delete operations with async SQLAlchemy support."
        
        return code, explanation
    
    def _generate_general_code(self, instruction: str, context: CodeContext = None) -> Tuple[str, str]:
        """Generate general purpose code"""
        function_name = self._generate_function_name(instruction)
        description = self._extract_description(instruction)
        params = self._extract_parameters(instruction)
        
        params_str = ", ".join([f"{p}: Any" for p in params]) if params else ""
        
        code = f'''from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def {function_name}({params_str}) -> Dict[str, Any]:
    """
    {description}
    
    Args:
        {chr(10 + 8).join([f"{p}: Description of {p}" for p in params]) if params else "No parameters"}
    
    Returns:
        Dict containing the result
    """
    try:
        # TODO: Implement the logic
        result = {{"success": True}}
        
        logger.info(f"{function_name} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error in {function_name}: {{e}}")
        raise
'''
        
        explanation = f"Generated a function '{function_name}' that {description.lower()}. Add your implementation logic in the try block."
        
        return code, explanation
    
    def _handle_explanation(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle code explanation tasks"""
        if not context or not context.surrounding_code:
            return CodeSuggestion(
                code="",
                explanation="Please provide the code you want me to explain.",
                confidence=0.5,
                task_type=TaskType.EXPLAIN,
            )
        
        code = context.surrounding_code
        explanation = self._explain_code(code)
        
        return CodeSuggestion(
            code=code,
            explanation=explanation,
            confidence=0.9,
            task_type=TaskType.EXPLAIN,
        )
    
    def _explain_code(self, code: str) -> str:
        """Generate explanation for code"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "Unable to parse code due to syntax error."
        
        explanations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = [arg.arg for arg in node.args.args]
                docstring = ast.get_docstring(node) or "No docstring"
                explanations.append(f"Function '{node.name}' takes parameters: {', '.join(params)}. {docstring}")
            
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                docstring = ast.get_docstring(node) or "No docstring"
                explanations.append(f"Class '{node.name}' with methods: {', '.join(methods)}. {docstring}")
        
        if explanations:
            return "\n".join(explanations)
        else:
            return "The code contains general logic without specific functions or classes."
    
    def _handle_refactoring(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle code refactoring tasks"""
        if not context or not context.surrounding_code:
            return CodeSuggestion(
                code="",
                explanation="Please provide the code you want me to refactor.",
                confidence=0.5,
                task_type=TaskType.REFACTOR,
            )
        
        original_code = context.surrounding_code
        refactored_code, changes = self._refactor_code(original_code, instruction)
        
        explanation = f"Applied the following refactoring changes:\n" + "\n".join([f"- {c}" for c in changes])
        
        return CodeSuggestion(
            code=refactored_code,
            explanation=explanation,
            confidence=0.85,
            task_type=TaskType.REFACTOR,
            improvements=changes,
        )
    
    def _refactor_code(self, code: str, instruction: str) -> Tuple[str, List[str]]:
        """Apply refactoring to code"""
        changes = []
        refactored = code
        
        instruction_lower = instruction.lower()
        
        if "type" in instruction_lower or "types" in instruction_lower:
            refactored = self._add_type_hints(refactored)
            changes.append("Added type hints to function parameters and returns")
        
        if "doc" in instruction_lower or "document" in instruction_lower:
            refactored = self._add_docstrings(refactored)
            changes.append("Added docstrings to functions and classes")
        
        if "simplify" in instruction_lower or "clean" in instruction_lower:
            refactored = self._simplify_code(refactored)
            changes.append("Simplified code structure")
        
        if not changes:
            refactored = self._apply_general_refactoring(refactored)
            changes.append("Applied general code improvements")
        
        return refactored, changes
    
    def _add_type_hints(self, code: str) -> str:
        """Add type hints to code"""
        lines = code.split('\n')
        result_lines = []
        
        for line in lines:
            if line.strip().startswith('def ') and '-> ' not in line:
                if line.rstrip().endswith(':'):
                    line = line.rstrip()[:-1] + ' -> Any:'
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _add_docstrings(self, code: str) -> str:
        """Add docstrings to functions"""
        lines = code.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            result_lines.append(line)
            
            if line.strip().startswith('def ') and i + 1 < len(lines):
                if not lines[i + 1].strip().startswith('"""') and not lines[i + 1].strip().startswith("'''"):
                    indent = len(line) - len(line.lstrip()) + 4
                    func_name = line.split('def ')[1].split('(')[0]
                    result_lines.append(' ' * indent + '"""')
                    result_lines.append(' ' * indent + f'{func_name} function')
                    result_lines.append(' ' * indent + '"""')
            
            i += 1
        
        return '\n'.join(result_lines)
    
    def _simplify_code(self, code: str) -> str:
        """Simplify code structure"""
        simplified = code
        
        simplified = re.sub(r'if True:', '', simplified)
        simplified = re.sub(r'if not False:', '', simplified)
        simplified = re.sub(r'pass\s*# .*', 'pass', simplified)
        
        return simplified
    
    def _apply_general_refactoring(self, code: str) -> str:
        """Apply general refactoring rules"""
        refactored = code
        
        refactored = self._add_type_hints(refactored)
        refactored = self._simplify_code(refactored)
        
        return refactored
    
    def _handle_debugging(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle debugging tasks"""
        issues = []
        fixes = []
        
        if context and context.surrounding_code:
            code = context.surrounding_code
            detected_issues = self._detect_issues(code)
            issues.extend(detected_issues)
            
            for issue in detected_issues:
                fix = self._suggest_fix(issue, code)
                if fix:
                    fixes.append(fix)
        
        explanation = "Detected the following issues:\n" + "\n".join([f"- {i}" for i in issues])
        if fixes:
            explanation += "\n\nSuggested fixes:\n" + "\n".join([f"- {f}" for f in fixes])
        
        return CodeSuggestion(
            code=context.surrounding_code if context else "",
            explanation=explanation,
            confidence=0.8,
            task_type=TaskType.DEBUG,
            issues=issues,
            improvements=fixes,
        )
    
    def _detect_issues(self, code: str) -> List[str]:
        """Detect issues in code"""
        issues = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
        
        if re.search(r'\bNone\s*\.\s*\w+', code):
            issues.append("Potential None reference - check for null before accessing attributes")
        
        if re.search(r'except\s*:', code):
            issues.append("Bare except clause - consider catching specific exceptions")
        
        if re.search(r'except Exception:', code) and not re.search(r'raise', code):
            issues.append("Catching Exception without re-raising may hide errors")
        
        if len(re.findall(r'print\(', code)) > 3:
            issues.append("Multiple print statements - consider using logging")
        
        return issues
    
    def _suggest_fix(self, issue: str, code: str) -> str:
        """Suggest fix for an issue"""
        if "Syntax error" in issue:
            return "Fix the syntax error by checking the line mentioned"
        elif "None reference" in issue:
            return "Add null check: if obj is not None: obj.method()"
        elif "Bare except" in issue:
            return "Replace 'except:' with 'except SpecificException:'"
        elif "print statements" in issue:
            return "Replace print() with logger.info() or logger.debug()"
        else:
            return "Review and fix the issue"
    
    def _handle_documentation(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle documentation generation tasks"""
        if not context or not context.surrounding_code:
            return CodeSuggestion(
                code="",
                explanation="Please provide the code you want to document.",
                confidence=0.5,
                task_type=TaskType.DOCUMENT,
            )
        
        code = context.surrounding_code
        documented_code = self._add_documentation(code)
        explanation = "Added documentation to the code including docstrings and comments."
        
        return CodeSuggestion(
            code=documented_code,
            explanation=explanation,
            confidence=0.85,
            task_type=TaskType.DOCUMENT,
        )
    
    def _add_documentation(self, code: str) -> str:
        """Add documentation to code"""
        documented = self._add_docstrings(code)
        
        lines = documented.split('\n')
        result = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and i + 1 < len(lines):
                indent = len(line) - len(line.lstrip())
                next_line = lines[i + 1]
                
                if not next_line.strip().startswith('"""'):
                    func_name = line.split('def ')[1].split('(')[0]
                    params = re.findall(r'\(([^)]*)\)', line)
                    
                    param_docs = ""
                    if params and params[0]:
                        for p in params[0].split(','):
                            p = p.strip().split(':')[0].split('=')[0].strip()
                            if p and p != 'self':
                                param_docs += f"\n{' ' * (indent + 4)}{p}: Description"
                    
                    result.append(line)
                    result.append(' ' * indent + '"""')
                    result.append(' ' * indent + f'{func_name} function')
                    if param_docs:
                        result.append(' ' * indent + '')
                        result.append(' ' * indent + 'Args:')
                        result.append(param_docs)
                    result.append(' ' * indent + '"""')
                    continue
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _handle_completion(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle code completion tasks"""
        if not context or not context.surrounding_code:
            return CodeSuggestion(
                code="",
                explanation="Please provide the code context for completion.",
                confidence=0.5,
                task_type=TaskType.COMPLETE,
            )
        
        code = context.surrounding_code
        completed_code = self._complete_code(code, instruction)
        
        return CodeSuggestion(
            code=completed_code,
            explanation="Completed the code based on the context.",
            confidence=0.8,
            task_type=TaskType.COMPLETE,
        )
    
    def _complete_code(self, code: str, instruction: str) -> str:
        """Complete partial code"""
        completed = code
        
        if code.rstrip().endswith('pass'):
            completed = code.rstrip()[:-4].rstrip()
            completed += "\n    # TODO: Implement this function\n    return None"
        
        if 'try:' in code and 'except' not in code:
            completed += "\n    except Exception as e:\n        logger.error(f'Error: {e}')\n        raise"
        
        if 'if ' in code and code.rstrip().endswith(':'):
            last_if = code.rstrip()[:-1]
            completed = code + "\n        # Add condition handling\n        pass"
        
        return completed
    
    def _handle_review(self, instruction: str, context: CodeContext = None) -> CodeSuggestion:
        """Handle code review tasks"""
        if not context or not context.surrounding_code:
            return CodeSuggestion(
                code="",
                explanation="Please provide the code you want me to review.",
                confidence=0.5,
                task_type=TaskType.REVIEW,
            )
        
        code = context.surrounding_code
        review = self._review_code(code)
        issues = self._detect_issues(code)
        improvements = self._suggest_improvements(code)
        
        return CodeSuggestion(
            code=code,
            explanation=review,
            confidence=0.9,
            task_type=TaskType.REVIEW,
            issues=issues,
            improvements=improvements,
        )
    
    def _review_code(self, code: str) -> str:
        """Review code and provide feedback"""
        review_points = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_complexity(node)
                    if complexity > 10:
                        review_points.append(f"Function '{node.name}' has high complexity ({complexity}). Consider breaking it down.")
                    
                    if not ast.get_docstring(node):
                        review_points.append(f"Function '{node.name}' is missing a docstring.")
                
                elif isinstance(node, ast.ClassDef):
                    if not ast.get_docstring(node):
                        review_points.append(f"Class '{node.name}' is missing a docstring.")
            
            if not review_points:
                review_points.append("Code looks good! No major issues found.")
            
        except SyntaxError:
            review_points.append("Syntax error in code. Please fix before review.")
        
        return "\n".join(review_points)
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _suggest_improvements(self, code: str) -> List[str]:
        """Suggest improvements for code"""
        improvements = []
        
        if 'print(' in code:
            improvements.append("Consider using logging instead of print statements")
        
        if re.search(r'# TODO|# FIXME|# XXX', code):
            improvements.append("Resolve TODO/FIXME comments")
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        improvements.append(f"Add docstring to function '{node.name}'")
        except:
            pass
        
        return improvements
    
    def _extract_path(self, instruction: str) -> str:
        """Extract API path from instruction"""
        match = re.search(r'/[\w/-]+', instruction)
        if match:
            return match.group(0).lstrip('/')
        return "items"
    
    def _generate_function_name(self, instruction: str) -> str:
        """Generate function name from instruction"""
        words = re.findall(r'\b\w+\b', instruction.lower())
        meaningful = [w for w in words if w not in ['create', 'generate', 'write', 'a', 'an', 'the', 'for', 'to', 'and', 'or']]
        return '_'.join(meaningful[:4]) if meaningful else 'process'
    
    def _extract_class_name(self, instruction: str) -> str:
        """Extract class name from instruction"""
        words = re.findall(r'\b\w+\b', instruction)
        meaningful = [w.capitalize() for w in words if w.lower() not in ['create', 'generate', 'class', 'a', 'an', 'the', 'for']]
        return ''.join(meaningful[:3]) if meaningful else 'Item'
    
    def _extract_description(self, instruction: str) -> str:
        """Extract description from instruction"""
        return instruction.strip()
    
    def _extract_fields(self, instruction: str) -> List[Tuple[str, str]]:
        """Extract fields from instruction"""
        fields = []
        
        field_patterns = [
            (r'id', 'int'),
            (r'name', 'str'),
            (r'email', 'str'),
            (r'description', 'Optional[str]'),
            (r'status', 'str'),
            (r'created', 'datetime'),
            (r'updated', 'Optional[datetime]'),
        ]
        
        for pattern, type_ in field_patterns:
            if pattern in instruction.lower():
                fields.append((pattern, type_))
        
        if not fields:
            fields = [('id', 'int'), ('name', 'str')]
        
        return fields
    
    def _extract_parameters(self, instruction: str) -> List[str]:
        """Extract parameters from instruction"""
        params = []
        
        if 'file' in instruction.lower():
            params.append('file_path')
        if 'data' in instruction.lower():
            params.append('data')
        if 'config' in instruction.lower():
            params.append('config')
        if 'id' in instruction.lower():
            params.append('id')
        
        return params
    
    def _extract_entity_name(self, instruction: str) -> str:
        """Extract entity name from instruction"""
        words = re.findall(r'\b\w+\b', instruction.lower())
        
        for w in words:
            if w not in ['create', 'generate', 'write', 'crud', 'for', 'a', 'an', 'the', 'operations']:
                return w
        
        return 'item'


class CodeSession:
    """
    Code session for managing conversations and context
    Similar to opencode's session management
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or self._generate_session_id()
        self.assistant = AICodeAssistant()
        self.history: List[Dict[str, Any]] = []
        self.files: Dict[str, str] = {}
        self.created_at = datetime.utcnow()
    
    def _generate_session_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def add_file(self, path: str, content: str):
        """Add a file to the session"""
        self.files[path] = content
    
    def get_file(self, path: str) -> Optional[str]:
        """Get file content"""
        return self.files.get(path)
    
    def process_instruction(self, instruction: str, file_path: str = None) -> CodeSuggestion:
        """Process an instruction with context"""
        context = CodeContext()
        
        if file_path and file_path in self.files:
            context.file_path = file_path
            context.surrounding_code = self.files[file_path]
        
        result = self.assistant.process_instruction(instruction, context)
        
        self.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "instruction": instruction,
            "file_path": file_path,
            "result": {
                "task_type": result.task_type.value,
                "confidence": result.confidence,
            }
        })
        
        return result
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.history


if __name__ == "__main__":
    assistant = AICodeAssistant()
    
    print("=== Test: Generate API Endpoint ===")
    result = assistant.process_instruction("Create a GET endpoint for fetching user profiles")
    print(f"Code:\n{result.code}")
    print(f"Explanation: {result.explanation}")
    
    print("\n=== Test: Generate Data Model ===")
    result = assistant.process_instruction("Create a Product model with id, name, price, and description")
    print(f"Code:\n{result.code}")
    
    print("\n=== Test: Code Review ===")
    code = "def process_data(data):\n    for item in data:\n        print(item)"
    ctx = CodeContext(surrounding_code=code)
    result = assistant.process_instruction("Review this code", ctx)
    print(f"Review:\n{result.explanation}")
    print(f"Issues: {result.issues}")
    print(f"Improvements: {result.improvements}")
