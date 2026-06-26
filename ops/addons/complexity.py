"""Plugin module for analyzing Python file cyclomatic complexity using Radon."""
import os
import sys
import subprocess
from kernel.registry import tool


def _ensure_radon_installed() -> bool:
    """Dynamically installs radon via pip if it is not present in the current environment."""
    try:
        import radon  # noqa: F401
        return True
    except ImportError:
        try:
            # Trigger dynamic self-healing pip installation
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "radon"],
                capture_output=True,
                text=True,
                timeout=60.0
            )
            return result.returncode == 0
        except Exception:
            return False


@tool(name="codecomplexity", category="Developer", desc="Analyze Python code cyclomatic complexity using Radon to identify hot spots.")
def codecomplexity(file_path: str) -> str:
    """Analyzes the cyclomatic complexity of functions and classes in a Python file.

    Dynamically installs 'radon' if missing, computes the complexity of every
    code block, and outputs a ranked markdown analysis report.

    Args:
        file_path (str): The absolute or relative path to the Python file to analyze.

    Returns:
        str: A detailed markdown cyclomatic complexity report.
    """
    if not os.path.exists(file_path):
        return f"Error: Target file not found at '{file_path}'"

    if not file_path.endswith(".py"):
        return "Error: Target file must be a Python (.py) file."

    # 1. Self-heal and verify radon is installed
    if not _ensure_radon_installed():
        return "Error: Failed to dynamically install/import the 'radon' complexity parser."

    try:
        # 2. Dynamic imports to avoid load-time import crashes
        from radon.visitors import ComplexityVisitor
        from radon.complexity import cc_rank

        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # 3. Build the AST and visit all complexity blocks
        visitor = ComplexityVisitor.from_code(code)
        blocks = visitor.blocks

        report = [
            f"# Cyclomatic Complexity Report: {os.path.basename(file_path)}",
            "",
            "| Type | Name | Complexity Skernel | Grade | Line No | Recommendation |",
            "| :--- | :--- | :---: | :---: | :---: | :--- |"
        ]

        if not blocks:
            report.append("| - | - | - | - | - | No class or function blocks detected. |")
            return "\n".join(report)

        total_complexity = 0
        for block in blocks:
            name = block.name
            # Block type details
            btype = "Function"
            if hasattr(block, "classname") and block.classname:
                btype = "Method"
                name = f"{block.classname}.{name}"
            elif block.is_method:
                btype = "Method"
            elif type(block).__name__ == "Class":
                btype = "Class"

            complexity = block.complexity
            total_complexity += complexity
            grade = cc_rank(complexity)

            # Recommendations based on Radon grading standard
            if grade == "A":
                rec = "Excellent (Simple, low risk block)"
            elif grade == "B":
                rec = "Good (Well structured, low risk)"
            elif grade == "C":
                rec = "Moderate (Moderately complex)"
            elif grade == "D":
                rec = "High (Complex, review and test carefully)"
            else:
                rec = "Very High (Extremely complex, refactoring recommended!)"

            report.append(
                f"| {btype} | `{name}` | {complexity} | **{grade}** | {block.lineno} | {rec} |"
            )

        avg_complexity = total_complexity / len(blocks)
        overall_grade = cc_rank(int(avg_complexity))

        report.append("")
        report.append("## Summary Analytics")
        report.append(f"- **Total Scanned Blocks**: {len(blocks)}")
        report.append(f"- **Average Cyclomatic Complexity**: {avg_complexity:.2f} (Grade: **{overall_grade}**)")

        return "\n".join(report)

    except Exception as e:
        return f"Error occurred during complexity analysis: {str(e)}"
