from typing import Any
import inspect
from server.tools.registry import registry

class ToolExecutor:
    async def execute(self, tool_call: dict[str, Any]) -> Any:
        name = tool_call.get("name")
        args = tool_call.get("arguments", {})

        if not name:
            return {"error": "No tool name provided."}

        try:
            tool = registry.get(name)["function"]
            result = tool(**args)

            if inspect.isawaitable(result):
                result = await result

            return result

        except KeyError:
            return {"error": f"Tool '{name}' not found."}
        except Exception as e:
            return {"error": str(e)}
