"""Pure manifest preparation for a private behavior-disabled benchmark copy."""
import xml.etree.ElementTree as ET


EXECUTION_TAGS = ("AddGameplayScripts", "AddUserInterfaces", "ReplaceUIScript")


def make_control_manifest(source: bytes) -> tuple[bytes, dict]:
    """Keep static content and identity; never install or claim native validity."""
    root = ET.fromstring(source)
    if root.tag != "Mod" or not root.get("id") or not root.get("version"):
        raise ValueError("Expected Mod root with id/version")
    groups = root.findall("InGameActions")
    if len(groups) != 1:
        raise ValueError("Expected exactly one direct InGameActions")
    in_game = groups[0]
    allowed = {node for node in in_game if node.tag in EXECUTION_TAGS}
    for node in root.iter():
        if node.tag in EXECUTION_TAGS and node not in allowed:
            raise ValueError("Unexpected execution component outside direct InGameActions")
    removed = []
    for tag in EXECUTION_TAGS:
        elements = in_game.findall(tag)
        if not elements:
            raise ValueError("Expected at least one " + tag)
        for element in elements:
            removed.append((tag, element.get("id")))
            in_game.remove(element)
    report = {
        "mod_id": root.get("id"),
        "mod_version": root.get("version"),
        "removed_count": len(removed),
        "removed": removed,
    }
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), report
