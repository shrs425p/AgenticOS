"""Module for example_plugin.py"""
from core.tool_registry import tool


@tool(desc="Automated description")
def calculate_tax(amount: float) -> float:
    """Calculates the tax for a given amount (15%)."""
    return amount * 0.15


@tool(name="greet_user", category="social", desc="Automated description")
def hello(name: str) -> str:
    """Greets the user with a friendly message."""
    return f"Hello, {name}! Welcome to the new modular AgenticOs."
