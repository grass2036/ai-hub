"""
代码分析和技术债务检测模块
Week 6 Day 3: 代码重构和架构优化 - 代码分析
实现代码质量分析、技术债务检测、重构建议等功能
"""

import ast
import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import subprocess
import importlib.util

logger = logging.getLogger(__name__)

@dataclass
class CodeMetrics:
    """代码指标"""
    file_path: str
    lines_of_code: int
    lines_of_comments: int
    complexity: int
    functions: int
    classes: int
    imports: int
    dependencies: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class TechnicalDebt:
    """技术债务"""
    type: str
    severity: str  # low, medium, high, critical
    description: str
    file_path: str
    line_number: int
    suggestion: str
    estimated_hours: float

@dataclass
class RefactoringSuggestion:
    """重构建议"""
    category: str
    priority: str
    description: str
    affected_files: List[str]
    benefits: List[str]
    effort_estimate: str

class CodeAnalyzer:
    """代码分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.code_metrics: Dict[str, CodeMetrics] = {}
        self.technical_debts: List[TechnicalDebt] = []
        self.refactoring_suggestions: List[RefactoringSuggestion] = []

    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目"""
        logger.info("开始代码结构分析...")

        # 分析Python文件
        python_files = self._find_python_files()
        for file_path in python_files:
            try:
                metrics = self._analyze_file(file_path)
                self.code_metrics[str(file_path)] = metrics
            except Exception as e:
                logger.error(f"分析文件失败 {file_path}: {e}")

        # 检测技术债务
        self._detect_technical_debt()

        # 生成重构建议
        self._generate_refactoring_suggestions()

        return self._generate_analysis_report()

    def _find_python_files(self) -> List[Path]:
        """查找Python文件"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 跳过常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return python_files

    def _analyze_file(self, file_path: Path) -> CodeMetrics:
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content)

            # 计算指标
            lines = content.split('\n')
            loc = len(lines)
            comment_lines = len([line for line in lines if line.strip().startswith('#')])

            # 计算复杂度
            complexity = self._calculate_complexity(tree)

            # 统计函数和类
            functions = len([node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))])
            classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])

            # 统计导入
            imports = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])

            # 提取依赖
            dependencies = self._extract_dependencies(tree)

            # 检测问题
            issues = self._detect_code_issues(tree, content)

            return CodeMetrics(
                file_path=str(file_path),
                lines_of_code=loc,
                lines_of_comments=comment_lines,
                complexity=complexity,
                functions=functions,
                classes=classes,
                imports=imports,
                dependencies=dependencies,
                issues=issues
            )

        except Exception as e:
            logger.error(f"文件分析失败 {file_path}: {e}")
            return CodeMetrics(file_path=str(file_path), lines_of_code=0, lines_of_comments=0, complexity=0, functions=0, classes=0, imports=0)

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _extract_dependencies(self, tree: ast.AST) -> List[str]:
        """提取依赖"""
        dependencies = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.append(node.module)

        return list(set(dependencies))

    def _detect_code_issues(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        """检测代码问题"""
        issues = []

        # 检测长函数
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > 50:
                    issues.append({
                        "type": "long_function",
                        "line": node.lineno,
                        "message": f"函数 '{node.name}' 过长 ({func_lines} 行)",
                        "severity": "medium"
                    })

        # 检测大类
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if class_lines > 200:
                    issues.append({
                        "type": "large_class",
                        "line": node.lineno,
                        "message": f"类 '{node.name}' 过大 ({class_lines} 行)",
                        "severity": "medium"
                    })

        # 检测重复代码
        lines = content.split('\n')
        repeated_lines = self._find_repeated_lines(lines)
        for line_info in repeated_lines:
            issues.append({
                "type": "duplicate_code",
                "line": line_info["line"],
                "message": f"疑似重复代码 (行 {line_info['line']})",
                "severity": "low"
            })

        return issues

    def _find_repeated_lines(self, lines: List[str], min_length: int = 5) -> List[Dict[str, int]]:
        """查找重复代码行"""
        repeated_lines = []

        for i, line in enumerate(lines):
            if len(line.strip()) < min_length:
                continue

            # 查找相似行
            for j in range(i + 1, len(lines)):
                other_line = lines[j]
                if len(other_line.strip()) < min_length:
                    continue

                # 简单的相似度检测
                similarity = self._calculate_similarity(line, other_line)
                if similarity > 0.8:
                    repeated_lines.append({
                        "line": i + 1,
                        "similar_line": j + 1,
                        "similarity": similarity
                    })
                    break

        return repeated_lines[:10]  # 限制返回数量

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度"""
        import difflib
        return difflib.SequenceMatcher(None, str1, str2).ratio()

    def _detect_technical_debt(self):
        """检测技术债务"""
        self.technical_debts = []

        for file_path, metrics in self.code_metrics.items():
            # 复杂度过高
            if metrics.complexity > 10:
                self.technical_debts.append(TechnicalDebt(
                    type="high_complexity",
                    severity="high" if metrics.complexity > 20 else "medium",
                    description=f"文件复杂度过高: {metrics.complexity}",
                    file_path=file_path,
                    line_number=1,
                    suggestion="重构函数，减少嵌套和条件分支",
                    estimated_hours=metrics.complexity * 0.5
                ))

            # 注释率过低
            comment_ratio = metrics.lines_of_comments / metrics.lines_of_code if metrics.lines_of_code > 0 else 0
            if comment_ratio < 0.1 and metrics.lines_of_code > 50:
                self.technical_debts.append(TechnicalDebt(
                    type="low_documentation",
                    severity="medium",
                    description=f"注释不足: {comment_ratio:.1%}",
                    file_path=file_path,
                    line_number=1,
                    suggestion="添加适当的文档注释",
                    estimated_hours=2.0
                ))

            # 依赖过多
            if len(metrics.dependencies) > 15:
                self.technical_debts.append(TechnicalDebt(
                    type="high_coupling",
                    severity="medium",
                    description=f"依赖过多: {len(metrics.dependencies)} 个模块",
                    file_path=file_path,
                    line_number=1,
                    suggestion="考虑使用依赖注入或接口抽象",
                    estimated_hours=4.0
                ))

    def _generate_refactoring_suggestions(self):
        """生成重构建议"""
        self.refactoring_suggestions = []

        # 分析模块化程度
        module_analysis = self._analyze_modularity()
        if module_analysis["needs_refactoring"]:
            self.refactoring_suggestions.append(RefactoringSuggestion(
                category="modularization",
                priority="high",
                description="改进模块化设计，减少模块间耦合",
                affected_files=module_analysis["affected_files"],
                benefits=["提高代码可维护性", "降低测试复杂度", "增强代码复用性"],
                effort_estimate="2-3天"
            ))

        # 分析API设计
        api_analysis = self._analyze_api_design()
        if api_analysis["needs_refactoring"]:
            self.refactoring_suggestions.append(RefactoringSuggestion(
                category="api_design",
                priority="medium",
                description="优化API接口设计，提高一致性和易用性",
                affected_files=api_analysis["affected_files"],
                benefits=["提升开发效率", "减少维护成本", "改善用户体验"],
                effort_estimate="1-2天"
            ))

        # 分析数据访问层
        data_analysis = self._analyze_data_access()
        if data_analysis["needs_refactoring"]:
            self.refactoring_suggestions.append(RefactoringSuggestion(
                category="data_access",
                priority="high",
                description="重构数据访问层，引入Repository模式",
                affected_files=data_analysis["affected_files"],
                benefits=["提高数据访问效率", "增强数据安全性", "简化测试"],
                effort_estimate="2-4天"
            ))

    def _analyze_modularity(self) -> Dict[str, Any]:
        """分析模块化程度"""
        # 计算模块间依赖
        dependency_graph = {}
        for file_path, metrics in self.code_metrics.items():
            dependency_graph[file_path] = metrics.dependencies

        # 检测循环依赖
        circular_deps = self._detect_circular_dependencies(dependency_graph)

        # 检测高耦合模块
        high_coupling_files = []
        for file_path, deps in dependency_graph.items():
            if len(deps) > 10:
                high_coupling_files.append(file_path)

        return {
            "needs_refactoring": len(circular_deps) > 0 or len(high_coupling_files) > 0,
            "circular_dependencies": circular_deps,
            "high_coupling_files": high_coupling_files,
            "affected_files": high_coupling_files + [dep[0] for dep in circular_deps]
        }

    def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """检测循环依赖"""
        circular_deps = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                for i in range(len(cycle) - 1):
                    circular_deps.append((cycle[i], cycle[i + 1]))
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            if node in dependency_graph:
                for dep in dependency_graph[node]:
                    dfs(dep, path + [node])

            rec_stack.remove(node)

        for file_path in dependency_graph:
            if file_path not in visited:
                dfs(file_path, [])

        return list(set(circular_deps))

    def _analyze_api_design(self) -> Dict[str, Any]:
        """分析API设计"""
        api_files = []
        for file_path in self.code_metrics:
            if "api" in file_path.lower():
                api_files.append(file_path)

        # 检查API文件的问题
        issues = []
        for file_path in api_files:
            metrics = self.code_metrics[file_path]
            if metrics.functions > 20:
                issues.append(f"{file_path}: 函数过多 ({metrics.functions})")
            if metrics.complexity > 15:
                issues.append(f"{file_path}: 复杂度过高 ({metrics.complexity})")

        return {
            "needs_refactoring": len(issues) > 0,
            "issues": issues,
            "affected_files": api_files
        }

    def _analyze_data_access(self) -> Dict[str, Any]:
        """分析数据访问层"""
        data_files = []
        for file_path in self.code_metrics:
            if any(keyword in file_path.lower() for keyword in ["model", "database", "db", "sql"]):
                data_files.append(file_path)

        # 检查数据访问问题
        issues = []
        for file_path in data_files:
            metrics = self.code_metrics[file_path]
            # 检查是否有直接SQL查询
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'SELECT' in content.upper() or 'INSERT' in content.upper():
                    issues.append(f"{file_path}: 包含直接SQL查询")

        return {
            "needs_refactoring": len(issues) > 0,
            "issues": issues,
            "affected_files": data_files
        }

    def _generate_analysis_report(self) -> Dict[str, Any]:
        """生成分析报告"""
        # 计算总体指标
        total_files = len(self.code_metrics)
        total_loc = sum(m.lines_of_code for m in self.code_metrics.values())
        total_complexity = sum(m.complexity for m in self.code_metrics.values())
        avg_complexity = total_complexity / total_files if total_files > 0 else 0

        # 按严重程度统计技术债务
        debt_by_severity = {}
        for debt in self.technical_debts:
            if debt.severity not in debt_by_severity:
                debt_by_severity[debt.severity] = 0
            debt_by_severity[debt.severity] += 1

        return {
            "summary": {
                "total_files": total_files,
                "total_lines_of_code": total_loc,
                "average_complexity": round(avg_complexity, 2),
                "total_functions": sum(m.functions for m in self.code_metrics.values()),
                "total_classes": sum(m.classes for m in self.code_metrics.values()),
                "technical_debt_count": len(self.technical_debts),
                "refactoring_suggestions": len(self.refactoring_suggestions)
            },
            "technical_debt": {
                "by_severity": debt_by_severity,
                "total_estimated_hours": sum(debt.estimated_hours for debt in self.technical_debts),
                "items": [
                    {
                        "type": debt.type,
                        "severity": debt.severity,
                        "description": debt.description,
                        "file_path": debt.file_path,
                        "suggestion": debt.suggestion,
                        "estimated_hours": debt.estimated_hours
                    }
                    for debt in sorted(self.technical_debts, key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}[x.severity], reverse=True)
                ]
            },
            "refactoring_suggestions": [
                {
                    "category": suggestion.category,
                    "priority": suggestion.priority,
                    "description": suggestion.description,
                    "affected_files": suggestion.affected_files,
                    "benefits": suggestion.benefits,
                    "effort_estimate": suggestion.effort_estimate
                }
                for suggestion in self.refactoring_suggestions
            ],
            "code_quality": {
                "files": [
                    {
                        "path": metrics.file_path,
                        "loc": metrics.lines_of_code,
                        "complexity": metrics.complexity,
                        "functions": metrics.functions,
                        "classes": metrics.classes,
                        "issues_count": len(metrics.issues)
                    }
                    for metrics in sorted(self.code_metrics.values(), key=lambda x: x.complexity, reverse=True)
                ]
            },
            "generated_at": datetime.now().isoformat()
        }

# 测试函数
def test_code_analysis():
    """测试代码分析功能"""
    print("🔍 测试代码分析功能...")

    analyzer = CodeAnalyzer("/Users/chiyingjie/code/git/ai-hub/backend")
    report = analyzer.analyze_project()

    print(f"\n📊 代码分析报告:")
    print(f"总文件数: {report['summary']['total_files']}")
    print(f"总代码行数: {report['summary']['total_lines_of_code']}")
    print(f"平均复杂度: {report['summary']['average_complexity']}")
    print(f"技术债务项: {report['summary']['technical_debt_count']}")
    print(f"重构建议: {report['summary']['refactoring_suggestions']}")

    if report['technical_debt']['items']:
        print(f"\n⚠️  主要技术债务:")
        for item in report['technical_debt']['items'][:5]:
            print(f"- {item['description']} ({item['severity']})")

    if report['refactoring_suggestions']:
        print(f"\n💡 重构建议:")
        for suggestion in report['refactoring_suggestions']:
            print(f"- {suggestion['description']} ({suggestion['priority']})")

if __name__ == "__main__":
    test_code_analysis()