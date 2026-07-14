from typing import Any, Callable

class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, schema: dict[str, Any]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.tools[name] = {
                "function": func,
                "schema": schema,
            }
            return func
        return decorator

    def get(self, name: str) -> dict[str, Any]:
        return self.tools[name]


registry = ToolRegistry()
