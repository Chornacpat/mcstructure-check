"""Inspect serialized state only. Never execute or include command text."""
from array import array
from math import prod
from re import fullmatch

from .nbt import Int, loads, loads_zlib_compound

COMMAND_BLOCKS = {
    "minecraft:command_block": "impulse",
    "minecraft:chain_command_block": "chain",
    "minecraft:repeating_command_block": "repeat",
}
FACINGS = {0: "down", 1: "up", 2: "north", 3: "south", 4: "west", 5: "east"}
MAX_VOLUME = 4_194_304
MAX_ISSUES = 10_000


def compound(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected a compound")
    return value


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def flag(value):
    return integer(value) and value in (0, 1)


def facing(value):
    if integer(value):
        return FACINGS.get(value)
    if isinstance(value, str) and value in FACINGS.values():
        return value
    return None


def inspect_bytes(data):
    """Return checked counts and local positions, without command text."""
    root = loads(data)
    version = root.get("format_version")
    if not integer(version) or version not in (1, 2):
        raise ValueError("unsupported format_version (expected 1 or 2)")
    compression = root.get("compression", Int(0))
    if not isinstance(compression, Int) or compression not in (0, 1):
        raise ValueError("compression: expected an NBT int, 0 or 1")
    if compression == 1 and version != 2:
        raise ValueError("zlib structure compression requires format_version 2")
    size = root.get("size")
    if not isinstance(size, list) or len(size) != 3 or not all(
        integer(i) and i > 0 for i in size
    ):
        raise ValueError("size: expected three positive integers")
    volume = prod(size)
    if volume > MAX_VOLUME:
        raise ValueError(f"structure exceeds {MAX_VOLUME} cells")
    structure = root.get("structure")
    if compression == 1:
        if not isinstance(structure, bytes):
            raise ValueError("compressed structure: expected an NBT byte array")
        structure = loads_zlib_compound(structure)
    else:
        structure = compound(structure, "structure")
    default = compound(compound(structure.get("palette"), "palette").get("default"),
                       "palette.default")
    palette = default.get("block_palette")
    if not isinstance(palette, list):
        raise ValueError("block_palette: expected a list")
    indices = structure.get("block_indices")
    if not isinstance(indices, list) or len(indices) not in ({2} if version == 1 else {1, 2}):
        raise ValueError("block_indices: wrong number of layers")
    commands = {}
    for i, entry in enumerate(palette):
        entry = compound(entry, "block_palette entry")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("block_palette entry has no valid name")
        if name in COMMAND_BLOCKS:
            commands[i] = (name, entry.get("states"))
    for layer in indices:
        if not isinstance(layer, (list, array)) or len(layer) != volume:
            raise ValueError("block_indices: a layer length differs from size")
        if any(not integer(p) or p < -1 or p >= len(palette) for p in layer):
            raise ValueError("block_indices: index outside palette")
    positions = compound(default.get("block_position_data", {}), "block_position_data")
    for key in positions:
        if not fullmatch(r"0|[1-9][0-9]{0,7}", key) or int(key) >= volume:
            raise ValueError("block_position_data: invalid position index")

    _, y_size, z_size = size
    issues = []
    issue_count = command_count = 0
    modes = {mode: 0 for mode in COMMAND_BLOCKS.values()}
    counts = {"error": 0, "warning": 0}

    def add(code, severity, message, index, name=None):
        nonlocal issue_count
        issue_count += 1
        counts[severity] += 1
        if len(issues) < MAX_ISSUES:
            x, rem = divmod(index, y_size * z_size)
            y, z = divmod(rem, z_size)
            entry = {"code": code, "severity": severity, "position": [x, y, z],
                     "index": index, "message": message}
            if name:
                entry["block"] = name
            issues.append(entry)

    for index, p in enumerate(indices[0]):
        if p not in commands:
            continue
        name, states = commands[p]
        command_count += 1
        modes[COMMAND_BLOCKS[name]] += 1
        if not isinstance(states, dict):
            states = {}
        directions = []
        if "facing_direction" in states:
            value = states["facing_direction"]
            directions.append(FACINGS.get(value) if integer(value) else None)
        if "minecraft:facing_direction" in states:
            directions.append(facing(states["minecraft:facing_direction"]))
        if not directions or None in directions or len(set(directions)) > 1:
            add("INVALID_FACING", "error", "缺少朝向、朝向无效或两个朝向字段冲突", index, name)
        palette_cond = states.get("conditional_bit")
        if not flag(palette_cond):
            add("INVALID_PALETTE_CONDITION", "warning", "方块条件位缺失或不是 0/1", index, name)
        meta = positions.get(str(index))
        actor = meta.get("block_entity_data") if isinstance(meta, dict) else None
        if not isinstance(actor, dict):
            add("MISSING_BLOCK_ENTITY", "error", "缺少有效的命令方块实体数据", index, name)
            continue
        if actor.get("id") != "CommandBlock":
            add("INVALID_BLOCK_ENTITY_ID", "error", "方块实体标识不是 CommandBlock", index, name)
        if "Command" not in actor:
            add("MISSING_COMMAND", "error", "缺少 Command 字段", index, name)
        elif not isinstance(actor["Command"], str):
            add("INVALID_COMMAND", "error", "Command 字段不是字符串", index, name)
        elif not actor["Command"].strip():
            add("EMPTY_COMMAND", "warning", "指令为空或仅包含空白", index, name)
        if "conditionalMode" in actor:
            entity_cond = actor["conditionalMode"]
            if not flag(entity_cond):
                add("INVALID_ENTITY_CONDITION", "error", "实体条件位不是 0/1", index, name)
            elif flag(palette_cond) and palette_cond != entity_cond:
                add("CONDITION_MISMATCH", "error", "方块与实体的条件位不一致", index, name)
        else:
            add("MISSING_ENTITY_CONDITION", "warning", "实体缺少 conditionalMode，无法对照条件位", index, name)
    if len(indices) == 2:
        for index, p in enumerate(indices[1]):
            if p in commands:
                add("COMMAND_IN_SECONDARY_LAYER", "error",
                    "命令方块出现在副层，无法按主层规则检查", index, commands[p][0])
    return {"schema_version": 1, "format_version": int(version), "size": list(map(int, size)),
            "command_block_count": command_count, "modes": modes, "issue_count": issue_count,
            "severity_counts": counts, "issues_truncated": issue_count > len(issues), "issues": issues}
