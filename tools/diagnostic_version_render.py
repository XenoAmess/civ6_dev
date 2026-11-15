"""Render the new diagnostic version without changing legacy template bytes."""


def render_helper(text: str, kind: str, source_version: int) -> str:
    if type(source_version) is not int or source_version not in (140, 141, 142, 143, 144, 145, 146,147,148):
        raise ValueError("Unsupported diagnostic source version")
    if not isinstance(text, str) or kind not in ("benchmark_end_bridge", "diagnostic_plan_stage"):
        raise ValueError("Unknown diagnostic helper")
    if source_version not in (143, 144, 145, 146,147,148):
        return text

    def once(old: str, new: str) -> None:
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"Nonunique source{source_version} helper anchor: {kind}")
        text = text.replace(old, new, 1)

    guard = "sourceVersion==140 or sourceVersion==141 or sourceVersion==142"
    once(guard, guard + "".join(f" or sourceVersion=={v}" for v in range(143, source_version + 1)))
    if kind == "benchmark_end_bridge":
        once("if sourceVersion~=142 then Error();return end",
             f"if sourceVersion~={source_version} then Error();return end")
        old, new, count = "baiqi142-pressure-paired-v1", f"baiqi{source_version}-pressure-paired-v1", 3
    else:
        once("assert(sourceVersion==142,'Pressure requires source142')",
             f"assert(sourceVersion=={source_version},'Pressure requires source{source_version}')")
        old, new, count = "baiqi142-pressure-stageA-v1", f"baiqi{source_version}-pressure-stageA-v1", 1
    if text.count(old) != count:
        raise ValueError(f"Unknown source{source_version} pressure tag inventory: {kind}")
    return text.replace(old, new)
