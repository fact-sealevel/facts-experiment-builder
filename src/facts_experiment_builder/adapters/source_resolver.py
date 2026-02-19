"""Resolve values from dot-separated source paths into a context (metadata, module_inputs)."""

from typing import Dict, Any


def resolve_value(source: str, context: Dict[str, Any]) -> Any:
    """
    Resolve a value from a source path like 'metadata.pipeline-id' or 'module_inputs.inputs.rcmip_fname'.

    The context dict typically has keys 'metadata' (experiment metadata) and 'module_inputs'
    (ModuleServiceSpecComponents or similar), so that source strings in module YAML can
    reference e.g. metadata.pipeline-id or module_inputs.outputs.foo.

    Args:
        source: Dot-separated path to the value (e.g. "metadata.pipeline-id", "module_inputs.inputs.location_file")
        context: Dict with at least 'metadata' and 'module_inputs' (or equivalent keys used in source strings)

    Returns:
        Resolved value, or None if any segment is missing
    """
    if not source or not isinstance(context, dict):
        return None

    parts = source.split(".")
    obj = context

    for part in parts:
        if obj is None:
            return None
        if isinstance(obj, dict):
            if part not in obj:
                snake_case = part.replace("-", "_")
                if snake_case in obj:
                    part = snake_case
                else:
                    obj = obj.get(part)
                    continue
            obj = obj.get(part)
        elif hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            snake_case = part.replace("-", "_")
            if hasattr(obj, snake_case):
                obj = getattr(obj, snake_case)
            else:
                return None

    return obj
