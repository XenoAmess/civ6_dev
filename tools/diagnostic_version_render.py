"""Render the new diagnostic version without changing legacy template bytes."""


def render_helper(text: str, kind: str, source_version: int) -> str:
    if type(source_version) is not int or source_version not in (140, 141, 142, 143):
        raise ValueError("Unsupported diagnostic source version")
    if not isinstance(text, str) or kind not in ("benchmark_end_bridge", "diagnostic_plan_stage"):
        raise ValueError("Unknown diagnostic helper")
    if source_version != 143:
        return text

    def once(old: str, new: str) -> None:
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"Nonunique source143 helper anchor: {kind}")
        text = text.replace(old, new, 1)

    once("sourceVersion==140 or sourceVersion==141 or sourceVersion==142",
         "sourceVersion==140 or sourceVersion==141 or sourceVersion==142 or sourceVersion==143")
    if kind == "benchmark_end_bridge":
        once("if sourceVersion~=142 then Error();return end",
             "if sourceVersion~=143 then Error();return end")
        old, new, count = "baiqi142-pressure-paired-v1", "baiqi143-pressure-paired-v1", 3
    else:
        once("assert(sourceVersion==142,'Pressure requires source142')",
             "assert(sourceVersion==143,'Pressure requires source143')")
        old, new, count = "baiqi142-pressure-stageA-v1", "baiqi143-pressure-stageA-v1", 1
    if text.count(old) != count:
        raise ValueError(f"Unknown source143 pressure tag inventory: {kind}")
    return text.replace(old, new)
