"""
代码质量改进和标准化模块
Week 6 Day 3: 代码重构和架构优化 - 代码质量改进
实现代码标准化、质量检查、自动化格式化等功能
"""

import ast
import re
import os
import subprocess
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from enum import Enum

logger = logging.getLogger(__name__)

class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class IssueType(Enum):
    """问题类型"""
    STYLE = "style"
    LOGIC = "logic"
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"

@dataclass
class CodeIssue:
    """代码问题"""
    file_path: str
    line_number: int
    column_number: int
    issue_type: IssueType
    severity: str  # info, warning, error, critical
    message: str
    rule_id: str
    suggestion: str = ""
    auto_fixable: bool = False

@dataclass
class QualityMetrics:
    """质量指标"""
    file_path: str
    lines_of_code: int
    complexity: int
    maintainability_index: float
    test_coverage: float
    duplication_percentage: float
    issues_count: int
    quality_score: float
    quality_level: QualityLevel

class CodeStandards:
    """代码标准配置"""

    # 命名规范
    NAMING_PATTERNS = {
        'class': r'^[A-Z][a-zA-Z0-9]*$',
        'function': r'^[a-z][a-zA-Z0-9_]*$',
        'variable': r'^[a-z][a-zA-Z0-9_]*$',
        'constant': r'^[A-Z][A-Z0-9_]*$',
        'module': r'^[a-z][a-z0-9_]*$'
    }

    # 复杂度限制
    MAX_FUNCTION_LENGTH = 50
    MAX_CLASS_LENGTH = 200
    MAX_NESTING_DEPTH = 4
    MAX_FUNCTION_COMPLEXITY = 10

    # 文档要求
    REQUIRE_DOCSTRINGS = True
    MIN_COMMENT_RATIO = 0.1

    # 性能要求
    MAX_IMPORTS_PER_FILE = 20
    MAX_DEPENDENCIES_PER_MODULE = 10

class CodeAnalyzer:
    """代码分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.standards = CodeStandards()
        self.issues: List[CodeIssue] = []
        self.metrics: Dict[str, QualityMetrics] = {}

    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目代码质量"""
        logger.info("开始代码质量分析...")

        python_files = self._find_python_files()

        for file_path in python_files:
            try:
                # 分析文件
                self._analyze_file(file_path)

                # 计算质量指标
                metrics = self._calculate_quality_metrics(file_path)
                self.metrics[str(file_path)] = metrics

            except Exception as e:
                logger.error(f"分析文件失败 {file_path}: {e}")

        return self._generate_quality_report()

    def _find_python_files(self) -> List[Path]:
        """查找Python文件"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 跳过忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                '__pycache__', 'venv', 'env', 'node_modules', 'migrations'
            ]]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return python_files

    def _analyze_file(self, file_path: Path):
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # 检查命名规范
            self._check_naming_conventions(tree, file_path)

            # 检查代码复杂度
            self._check_complexity(tree, file_path)

            # 检查文档
            self._check_documentation(tree, content, file_path)

            # 检查代码风格
            self._check_code_style(content, file_path)

            # 检查导入
            self._check_imports(tree, file_path)

            # 检查安全性
            self._check_security(content, file_path)

            # 检查性能问题
            self._check_performance_issues(content, file_path)

        except Exception as e:
            logger.error(f"文件分析失败 {file_path}: {e}")

    def _check_naming_conventions(self, tree: ast.AST, file_path: Path):
        """检查命名规范"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._check_name(node.name, 'class', node.lineno, node.col_offset, file_path)

                # 检查方法命名
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith('_') or item.name.startswith('__'):
                            self._check_name(item.name, 'function', item.lineno, item.col_offset, file_path)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not hasattr(node, 'parent_class'):  # 不在类中的函数
                    self._check_name(node.name, 'function', node.lineno, node.col_offset, file_path)

            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                # 检查变量命名
                if node.id.isupper():
                    self._check_name(node.id, 'constant', node.lineno, node.col_offset, file_path)
                else:
                    self._check_name(node.id, 'variable', node.lineno, node.col_offset, file_path)

    def _check_name(self, name: str, name_type: str, line: int, col: int, file_path: Path):
        """检查名称是否符合规范"""
        pattern = self.standards.NAMING_PATTERNS.get(name_type)
        if pattern and not re.match(pattern, name):
            self.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=line,
                column_number=col,
                issue_type=IssueType.NAMING,
                severity="warning",
                message=f"{name_type}命名不规范: '{name}'",
                rule_id=f"NAMING_{name_type.upper()}",
                suggestion=f"应符合模式: {pattern}",
                auto_fixable=False
            ))

    def _check_complexity(self, tree: ast.AST, file_path: Path):
        """检查代码复杂度"""
        # 检查函数长度
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_length = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0

                if func_length > self.standards.MAX_FUNCTION_LENGTH:
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column_number=0,
                        issue_type=IssueType.MAINTAINABILITY,
                        severity="warning",
                        message=f"函数过长: {func_length} 行 (建议 < {self.standards.MAX_FUNCTION_LENGTH})",
                        rule_id="FUNCTION_LENGTH",
                        suggestion="考虑拆分为更小的函数",
                        auto_fixable=False
                    ))

                # 检查复杂度
                complexity = self._calculate_function_complexity(node)
                if complexity > self.standards.MAX_FUNCTION_COMPLEXITY:
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column_number=0,
                        issue_type=IssueType.MAINTAINABILITY,
                        severity="warning",
                        message=f"函数复杂度过高: {complexity} (建议 < {self.standards.MAX_FUNCTION_COMPLEXITY})",
                        rule_id="FUNCTION_COMPLEXITY",
                        suggestion="简化逻辑或提取子函数",
                        auto_fixable=False
                    ))

        # 检查类长度
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_length = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0

                if class_length > self.standards.MAX_CLASS_LENGTH:
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column_number=0,
                        issue_type=IssueType.MAINTAINABILITY,
                        severity="warning",
                        message=f"类过长: {class_length} 行 (建议 < {self.standards.MAX_CLASS_LENGTH})",
                        rule_id="CLASS_LENGTH",
                        suggestion="考虑拆分为多个类或使用组合",
                        auto_fixable=False
                    ))

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """计算函数复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ListComp) or isinstance(child, ast.DictComp):
                complexity += 1

        return complexity

    def _check_documentation(self, tree: ast.AST, content: str, file_path: Path):
        """检查文档"""
        lines = content.split('\n')
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

        comment_ratio = comment_lines / code_lines if code_lines > 0 else 0

        if comment_ratio < self.standards.MIN_COMMENT_RATIO and code_lines > 20:
            self.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=1,
                column_number=0,
                issue_type=IssueType.DOCUMENTATION,
                severity="info",
                message=f"注释比例过低: {comment_ratio:.1%} (建议 > {self.standards.MIN_COMMENT_RATIO:.1%})",
                rule_id="COMMENT_RATIO",
                suggestion="添加适当的注释和文档字符串",
                auto_fixable=False
            ))

        # 检查函数文档字符串
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node) and node.name != '__init__':
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        column_number=0,
                        issue_type=IssueType.DOCUMENTATION,
                        severity="info",
                        message=f"函数 '{node.name}' 缺少文档字符串",
                        rule_id="DOCSTRING_MISSING",
                        suggestion="添加函数文档字符串",
                        auto_fixable=False
                    ))

    def _check_code_style(self, content: str, file_path: Path):
        """检查代码风格"""
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # 检查行长度
            if len(line) > 120:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column_number=120,
                    issue_type=IssueType.STYLE,
                    severity="info",
                    message=f"行过长: {len(line)} 字符 (建议 < 120)",
                    rule_id="LINE_LENGTH",
                    suggestion="换行或简化表达式",
                    auto_fixable=True
                ))

            # 检查尾随空格
            if line.endswith(' '):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column_number=len(line.rstrip()),
                    issue_type=IssueType.STYLE,
                    severity="info",
                    message="行尾有多余空格",
                    rule_id="TRAILING_WHITESPACE",
                    suggestion="删除行尾空格",
                    auto_fixable=True
                ))

            # 检查制表符
            if '\t' in line:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column_number=line.find('\t'),
                    issue_type=IssueType.STYLE,
                    severity="warning",
                    message="使用了制表符（建议使用空格）",
                    rule_id="TAB_CHARACTER",
                    suggestion="将制表符替换为空格",
                    auto_fixable=True
                ))

    def _check_imports(self, tree: ast.AST, file_path: Path):
        """检查导入"""
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]

        if len(imports) > self.standards.MAX_IMPORTS_PER_FILE:
            self.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=1,
                column_number=0,
                issue_type=IssueType.MAINTAINABILITY,
                severity="warning",
                message=f"导入过多: {len(imports)} 个 (建议 < {self.standards.MAX_IMPORTS_PER_FILE})",
                rule_id="IMPORT_COUNT",
                suggestion="考虑重新组织代码或减少依赖",
                auto_fixable=False
            ))

        # 检查未使用的导入
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    name = alias.asname if alias.asname else alias.name
                    if name not in used_names:
                        self.issues.append(CodeIssue(
                            file_path=str(file_path),
                            line_number=imp.lineno,
                            column_number=imp.col_offset,
                            issue_type=IssueType.MAINTAINABILITY,
                            severity="info",
                            message=f"未使用的导入: {name}",
                            rule_id="UNUSED_IMPORT",
                            suggestion="删除未使用的导入",
                            auto_fixable=True
                        ))

    def _check_security(self, content: str, file_path: Path):
        """检查安全问题"""
        lines = content.split('\n')

        # 检查硬编码密码
        password_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'passwd\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]

        for i, line in enumerate(lines, 1):
            for pattern in password_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=i,
                        column_number=0,
                        issue_type=IssueType.SECURITY,
                        severity="critical",
                        message="检测到硬编码的敏感信息",
                        rule_id="HARDCODED_SECRET",
                        suggestion="使用环境变量或配置文件",
                        auto_fixable=False
                    ))

        # 检查SQL注入风险
        sql_patterns = [
            r'execute\s*\(\s*["\'].*\+.*["\']',
            r'query\s*\(\s*["\'].*\+.*["\']'
        ]

        for i, line in enumerate(lines, 1):
            for pattern in sql_patterns:
                if re.search(pattern, line):
                    self.issues.append(CodeIssue(
                        file_path=str(file_path),
                        line_number=i,
                        column_number=0,
                        issue_type=IssueType.SECURITY,
                        severity="critical",
                        message="可能存在SQL注入风险",
                        rule_id="SQL_INJECTION",
                        suggestion="使用参数化查询",
                        auto_fixable=False
                    ))

    def _check_performance_issues(self, content: str, file_path: Path):
        """检查性能问题"""
        lines = content.split('\n')

        # 检查循环中的重复计算
        for i, line in enumerate(lines, 1):
            # 检查在循环中调用len()
            if re.search(r'for.*in.*range\s*\(\s*len\s*\(', line):
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column_number=0,
                    issue_type=IssueType.PERFORMANCE,
                    severity="info",
                    message="循环中重复计算len()",
                    rule_id="LEN_IN_LOOP",
                    suggestion="在循环外计算len()",
                    auto_fixable=False
                ))

            # 检查列表推导式中的复杂操作
            if 'for' in line and 'in' in line and line.count('[') > 1:
                self.issues.append(CodeIssue(
                    file_path=str(file_path),
                    line_number=i,
                    column_number=0,
                    issue_type=IssueType.PERFORMANCE,
                    severity="info",
                    message="复杂的列表推导式可能影响性能",
                    rule_id="COMPLEX_LIST_COMPREHENSION",
                    suggestion="考虑使用生成器或普通循环",
                    auto_fixable=False
                ))

    def _calculate_quality_metrics(self, file_path: Path) -> QualityMetrics:
        """计算质量指标"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            lines = content.split('\n')

            # 基础指标
            loc = len([line for line in lines if line.strip()])
            complexity = self._calculate_file_complexity(tree)

            # 可维护性指数（简化版）
            maintainability_index = max(0, 100 - complexity * 2)

            # 测试覆盖率（模拟）
            test_coverage = 0.0  # 实际应该从测试工具获取

            # 重复率（模拟）
            duplication_percentage = 0.0  # 实际应该计算代码重复

            # 问题数量
            issues_count = len([issue for issue in self.issues if issue.file_path == str(file_path)])

            # 质量评分
            quality_score = max(0, 100 - issues_count * 5 - complexity * 2)

            # 质量等级
            if quality_score >= 90:
                quality_level = QualityLevel.EXCELLENT
            elif quality_score >= 75:
                quality_level = QualityLevel.GOOD
            elif quality_score >= 60:
                quality_level = QualityLevel.FAIR
            else:
                quality_level = QualityLevel.POOR

            return QualityMetrics(
                file_path=str(file_path),
                lines_of_code=loc,
                complexity=complexity,
                maintainability_index=maintainability_index,
                test_coverage=test_coverage,
                duplication_percentage=duplication_percentage,
                issues_count=issues_count,
                quality_score=quality_score,
                quality_level=quality_level
            )

        except Exception as e:
            logger.error(f"计算质量指标失败 {file_path}: {e}")
            return QualityMetrics(
                file_path=str(file_path),
                lines_of_code=0,
                complexity=0,
                maintainability_index=0,
                test_coverage=0,
                duplication_percentage=0,
                issues_count=0,
                quality_score=0,
                quality_level=QualityLevel.POOR
            )

    def _calculate_file_complexity(self, tree: ast.AST) -> int:
        """计算文件复杂度"""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += self._calculate_function_complexity(node)
            elif isinstance(node, ast.ClassDef):
                complexity += 1  # 类本身的复杂度
        return complexity

    def _generate_quality_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        # 统计问题
        issues_by_type = {}
        issues_by_severity = {}
        auto_fixable_count = 0

        for issue in self.issues:
            # 按类型统计
            if issue.issue_type.value not in issues_by_type:
                issues_by_type[issue.issue_type.value] = 0
            issues_by_type[issue.issue_type.value] += 1

            # 按严重程度统计
            if issue.severity not in issues_by_severity:
                issues_by_severity[issue.severity] = 0
            issues_by_severity[issue.severity] += 1

            # 统计可自动修复
            if issue.auto_fixable:
                auto_fixable_count += 1

        # 计算总体指标
        total_files = len(self.metrics)
        total_loc = sum(m.lines_of_code for m in self.metrics.values())
        avg_complexity = sum(m.complexity for m in self.metrics.values()) / total_files if total_files > 0 else 0
        avg_quality_score = sum(m.quality_score for m in self.metrics.values()) / total_files if total_files > 0 else 0

        # 质量分布
        quality_distribution = {}
        for level in QualityLevel:
            quality_distribution[level.value] = len([m for m in self.metrics.values() if m.quality_level == level])

        return {
            "summary": {
                "total_files": total_files,
                "total_lines_of_code": total_loc,
                "average_complexity": round(avg_complexity, 2),
                "average_quality_score": round(avg_quality_score, 2),
                "total_issues": len(self.issues),
                "auto_fixable_issues": auto_fixable_count
            },
            "issues": {
                "by_type": issues_by_type,
                "by_severity": issues_by_severity,
                "items": [
                    {
                        "file_path": issue.file_path,
                        "line_number": issue.line_number,
                        "column_number": issue.column_number,
                        "type": issue.issue_type.value,
                        "severity": issue.severity,
                        "message": issue.message,
                        "rule_id": issue.rule_id,
                        "suggestion": issue.suggestion,
                        "auto_fixable": issue.auto_fixable
                    }
                    for issue in sorted(self.issues, key=lambda x: (
                        {"critical": 4, "error": 3, "warning": 2, "info": 1}[x.severity],
                        x.line_number
                    ), reverse=True)
                ]
            },
            "quality_metrics": {
                "distribution": quality_distribution,
                "files": [
                    {
                        "file_path": metrics.file_path,
                        "lines_of_code": metrics.lines_of_code,
                        "complexity": metrics.complexity,
                        "maintainability_index": metrics.maintainability_index,
                        "quality_score": metrics.quality_score,
                        "quality_level": metrics.quality_level.value,
                        "issues_count": metrics.issues_count
                    }
                    for metrics in sorted(self.metrics.values(), key=lambda x: x.quality_score)
                ]
            },
            "generated_at": datetime.now().isoformat()
        }

class CodeFormatter:
    """代码格式化工具"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def format_project(self) -> Dict[str, Any]:
        """格式化整个项目"""
        results = {
            "black": self._run_black(),
            "isort": self._run_isort(),
            "autopep8": self._run_autopep8()
        }

        return {
            "success": all(result["success"] for result in results.values()),
            "tools": results
        }

    def _run_black(self) -> Dict[str, Any]:
        """运行Black格式化"""
        try:
            result = subprocess.run(
                ["black", "--check", "--diff", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "needs_formatting": result.returncode != 0
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "格式化超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_isort(self) -> Dict[str, Any]:
        """运行isort排序导入"""
        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "needs_sorting": result.returncode != 0
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "排序超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_autopep8(self) -> Dict[str, Any]:
        """运行autopep8"""
        try:
            result = subprocess.run(
                ["autopep8", "--diff", "--recursive", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "needs_fixing": result.stdout.strip() != ""
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "修复超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

class CodeQualityManager:
    """代码质量管理器"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.analyzer = CodeAnalyzer(project_root)
        self.formatter = CodeFormatter(project_root)

    def run_quality_check(self) -> Dict[str, Any]:
        """运行完整的代码质量检查"""
        logger.info("开始代码质量检查...")

        # 代码分析
        analysis_report = self.analyzer.analyze_project()

        # 代码格式化检查
        format_report = self.formatter.format_project()

        return {
            "analysis": analysis_report,
            "formatting": format_report,
            "overall_quality": self._calculate_overall_quality(analysis_report, format_report)
        }

    def _calculate_overall_quality(self, analysis_report: Dict, format_report: Dict) -> Dict[str, Any]:
        """计算总体质量评分"""
        quality_score = analysis_report["summary"]["average_quality_score"]

        # 格式化影响评分
        if not format_report["success"]:
            quality_score -= 10

        # 确定等级
        if quality_score >= 90:
            grade = "A"
        elif quality_score >= 80:
            grade = "B"
        elif quality_score >= 70:
            grade = "C"
        elif quality_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": max(0, quality_score),
            "grade": grade,
            "status": "excellent" if grade in ["A", "B"] else "needs_improvement"
        }

# 测试函数
def test_code_quality():
    """测试代码质量检查"""
    print("🔍 测试代码质量检查...")

    quality_manager = CodeQualityManager("/Users/chiyingjie/code/git/ai-hub/backend")
    report = quality_manager.run_quality_check()

    print(f"\n📊 代码质量报告:")
    print(f"总文件数: {report['analysis']['summary']['total_files']}")
    print(f"总代码行数: {report['analysis']['summary']['total_lines_of_code']}")
    print(f"平均质量评分: {report['analysis']['summary']['average_quality_score']}")
    print(f"总问题数: {report['analysis']['summary']['total_issues']}")
    print(f"可自动修复: {report['analysis']['summary']['auto_fixable_issues']}")

    print(f"\n📝 格式化检查:")
    print(f"格式化状态: {'通过' if report['formatting']['success'] else '需要格式化'}")

    print(f"\n🎯 总体质量:")
    print(f"评分: {report['overall_quality']['score']}")
    print(f"等级: {report['overall_quality']['grade']}")
    print(f"状态: {report['overall_quality']['status']}")

if __name__ == "__main__":
    test_code_quality()