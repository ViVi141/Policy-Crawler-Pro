#!/usr/bin/env python3
"""
批量检查 Python 文件中的类型不兼容和其他问题
"""

import ast
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
import argparse


class TypeChecker(ast.NodeVisitor):
    """AST 访问者，检查类型问题"""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[Dict[str, Any]] = []
        self.current_function = None
        self.current_class = None
        self.imports: Dict[str, str] = {}  # name -> module
        self.variables: Dict[str, Any] = {}  # 变量类型信息

    def visit_Import(self, node):
        """记录导入"""
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """记录从模块导入"""
        module = node.module or ""
        for alias in node.names:
            self.imports[alias.asname or alias.name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """检查函数定义"""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_ClassDef(self, node):
        """检查类定义"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Assign(self, node):
        """检查赋值语句"""
        # 检查多重赋值
        if len(node.targets) > 1:
            self._check_multiple_assignment(node)

        # 检查每个目标
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_assignment(target, node.value, node)
            elif isinstance(target, ast.Attribute):
                self._check_attribute_assignment(target, node.value, node)
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                self._check_unpacking_assignment(target, node.value, node)

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        """检查带类型注解的赋值"""
        if node.annotation and node.value:
            self._check_type_annotation(node.target, node.annotation, node.value, node)
        self.generic_visit(node)

    def _check_multiple_assignment(self, node):
        """检查多重赋值"""
        if isinstance(node.value, (ast.Tuple, ast.List)):
            value_count = len(node.value.elts) if hasattr(node.value, "elts") else 0
            target_count = len(node.targets)
            if value_count > 0 and value_count != target_count:
                self._add_issue(
                    "multiple_assignment_mismatch",
                    node.lineno,
                    f"多重赋值数量不匹配: {target_count} 个目标, {value_count} 个值",
                )

    def _check_assignment(self, target: ast.Name, value: ast.AST, node: ast.Assign):
        """检查普通赋值"""
        # 检查 None 赋值
        if isinstance(value, ast.Constant) and value.value is None:
            # None 赋值通常是合法的，但可以记录
            pass

        # 检查类型不匹配的常见模式
        if isinstance(value, ast.Call):
            self._check_call_assignment(target, value, node)

        # 检查字符串和数字的混合
        if isinstance(value, ast.BinOp):
            self._check_binop_assignment(target, value, node)

    def _check_attribute_assignment(self, target: ast.Attribute, value: ast.AST, node: ast.Assign):
        """检查属性赋值"""
        # 属性赋值通常是合法的（obj.attr = value），这里不检查
        # 只检查明显的问题，比如对字面量的属性赋值
        if isinstance(target.value, ast.Constant):
            # 对常量进行属性赋值是无效的
            if isinstance(target.value.value, (int, float, str, bool, tuple)):
                self._add_issue(
                    "invalid_attribute_assignment",
                    node.lineno,
                    f"尝试对常量 {type(target.value.value).__name__} 进行属性赋值（无效操作）",
                )

    def _check_unpacking_assignment(self, target: ast.AST, value: ast.AST, node: ast.Assign):
        """检查解包赋值"""
        if isinstance(target, (ast.Tuple, ast.List)):
            target_count = len(target.elts) if hasattr(target, "elts") else 0
            if isinstance(value, (ast.Tuple, ast.List)):
                value_count = len(value.elts) if hasattr(value, "elts") else 0
                if target_count != value_count:
                    self._add_issue(
                        "unpacking_mismatch",
                        node.lineno,
                        f"解包数量不匹配: {target_count} 个目标, {value_count} 个值",
                    )

    def _check_call_assignment(self, target: ast.Name, call: ast.Call, node: ast.Assign):
        """检查函数调用赋值"""
        # 检查常见的类型不匹配
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
            # 检查可能返回 None 的函数
            if func_name in ["get", "find", "first"]:
                # 这些函数可能返回 None，但赋值可能期望非 None 值
                pass

    def _check_binop_assignment(self, target: ast.Name, binop: ast.BinOp, node: ast.Assign):
        """检查二元运算赋值"""
        # 检查字符串和数字的混合运算
        if isinstance(binop.op, (ast.Add, ast.Mult)):
            left_type = self._get_expression_type(binop.left)
            right_type = self._get_expression_type(binop.right)
            if left_type and right_type and left_type != right_type:
                if (left_type == "str" and right_type in ("int", "float")) or (
                    left_type in ("int", "float") and right_type == "str"
                ):
                    self._add_issue(
                        "type_mismatch",
                        node.lineno,
                        f"可能的类型不匹配: {left_type} 和 {right_type} 的运算",
                    )

    def _check_type_annotation(self, target: ast.AST, annotation: ast.AST, value: ast.AST, node: ast.AnnAssign):
        """检查类型注解与实际值的匹配"""
        # 这里可以添加更复杂的类型检查逻辑
        pass

    def _get_expression_type(self, node: ast.AST) -> Optional[str]:
        """获取表达式的类型"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return "str"
            elif isinstance(node.value, (int, float)):
                return "number"
            elif isinstance(node.value, bool):
                return "bool"
            elif node.value is None:
                return "None"
        elif isinstance(node, ast.Name):
            # 尝试从变量信息中获取类型
            if node.id in self.variables:
                return self.variables[node.id]
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                # 一些常见函数的返回类型
                if func_name in ["str", "int", "float", "bool"]:
                    return func_name
        return None

    def _add_issue(self, issue_type: str, lineno: int, message: str):
        """添加问题"""
        self.issues.append(
            {
                "type": issue_type,
                "line": lineno,
                "message": message,
                "file": self.filename,
                "function": self.current_function,
                "class": self.current_class,
            }
        )

    def visit_Compare(self, node):
        """检查比较操作"""
        # 检查类型不匹配的比较
        for i, comparator in enumerate(node.comparators):
            left_type = self._get_expression_type(node.left)
            right_type = self._get_expression_type(comparator)
            if left_type and right_type and left_type != right_type:
                # 某些比较可能是合法的（如 None 比较）
                if left_type != "None" and right_type != "None":
                    self._add_issue(
                        "type_comparison",
                        node.lineno,
                        f"可能的类型不匹配比较: {left_type} 和 {right_type}",
                    )
        self.generic_visit(node)

    def visit_Call(self, node):
        """检查函数调用"""
        # 检查参数类型
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            # 检查常见的问题
            if func_name == "len" and node.args:
                arg_type = self._get_expression_type(node.args[0])
                if arg_type and arg_type not in ("str", "list", "dict", "tuple"):
                    self._add_issue(
                        "invalid_len_argument",
                        node.lineno,
                        f"len() 的参数类型可能不正确: {arg_type}",
                    )
        self.generic_visit(node)


def check_file(filepath: Path) -> List[Dict[str, Any]]:
    """检查单个文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(filepath))
        checker = TypeChecker(str(filepath))
        checker.visit(tree)
        return checker.issues
    except SyntaxError as e:
        return [
            {
                "type": "syntax_error",
                "line": e.lineno or 0,
                "message": f"语法错误: {e.msg}",
                "file": str(filepath),
            }
        ]
    except Exception as e:
        return [
            {
                "type": "parse_error",
                "line": 0,
                "message": f"解析错误: {str(e)}",
                "file": str(filepath),
            }
        ]


def find_python_files(directory: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """查找所有 Python 文件"""
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".git", "node_modules", "venv", ".venv", "migrations"]

    python_files = []
    for root, dirs, files in os.walk(directory):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return sorted(python_files)


def format_issue(issue: Dict[str, Any]) -> str:
    """格式化问题输出"""
    location = f"{issue['file']}:{issue['line']}"
    if issue.get("function"):
        location += f" (函数: {issue['function']})"
    if issue.get("class"):
        location = f"{location} (类: {issue['class']})"
    return f"{location} - [{issue['type']}] {issue['message']}"


def main():
    parser = argparse.ArgumentParser(description="批量检查 Python 文件中的类型问题")
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="要检查的目录（默认: 当前目录）",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=["__pycache__", ".git", "node_modules", "venv", ".venv"],
        help="要排除的目录",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="显示问题摘要",
    )
    parser.add_argument(
        "--group-by-type",
        action="store_true",
        help="按问题类型分组显示",
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"错误: 目录不存在: {directory}")
        sys.exit(1)

    print(f"正在检查目录: {directory}")
    print(f"排除目录: {', '.join(args.exclude)}")
    print("-" * 80)

    python_files = find_python_files(directory, args.exclude)
    print(f"找到 {len(python_files)} 个 Python 文件\n")

    all_issues = []
    for filepath in python_files:
        issues = check_file(filepath)
        all_issues.extend(issues)

    if not all_issues:
        print("✅ 未发现任何问题！")
        sys.exit(0)

    # 按类型分组
    issues_by_type = defaultdict(list)
    for issue in all_issues:
        issues_by_type[issue["type"]].append(issue)

    # 显示结果
    if args.group_by_type:
        print("按类型分组的问题:\n")
        for issue_type, issues in sorted(issues_by_type.items()):
            print(f"\n[{issue_type}] ({len(issues)} 个问题):")
            for issue in issues:
                print(f"  {format_issue(issue)}")
    else:
        print("发现的问题:\n")
        for issue in all_issues:
            print(format_issue(issue))

    # 显示摘要
    if args.summary or len(all_issues) > 20:
        print("\n" + "=" * 80)
        print("问题摘要:")
        print(f"  总文件数: {len(python_files)}")
        print(f"  总问题数: {len(all_issues)}")
        print("  问题类型分布:")
        for issue_type, issues in sorted(issues_by_type.items()):
            print(f"    {issue_type}: {len(issues)} 个")

    # 返回退出码
    sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()

