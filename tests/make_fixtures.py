"""Write original synthetic Bedrock little-endian NBT fixtures."""

from pathlib import Path
import struct
import sys
import zlib

OMIT = object()


def integer(value):
    return (3, struct.pack("<i", value))


def byte(value):
    return (1, struct.pack("<b", value))


def string_bytes(value):
    encoded = value.encode("utf-8")
    return struct.pack("<H", len(encoded)) + encoded


def string(value):
    return (8, string_bytes(value))


def list_tag(kind, values):
    items = list(values)
    if any(tag != kind for tag, _ in items):
        raise ValueError("heterogeneous test list")
    return (9, struct.pack("<Bi", kind, len(items)) + b"".join(p for _, p in items))


def int_array(values):
    return (11, struct.pack(f"<i{len(values)}i", len(values), *values))


def byte_array(raw):
    return (7, struct.pack("<i", len(raw)) + raw)


def compound(fields):
    return (10, b"".join(bytes([tag]) + string_bytes(key) + value
                         for key, (tag, value) in fields.items()) + b"\x00")


def make_structure(blocks, *, size=(3, 2, 2), version=1, first_index=None,
                   compression_tag=OMIT, encode_structure=None):
    """Each block is (position, name suffix, facing, conditional bit, entity condition, command)."""
    xlen, ylen, zlen = size
    volume = xlen * ylen * zlen
    primary = [-1] * volume
    palette = []
    positions = {}
    for (x, y, z), suffix, facing, conditional, condition_mode, command in blocks:
        index = x * ylen * zlen + y * zlen + z
        states = {"conditional_bit": byte(conditional)}
        if facing is not OMIT:
            states["facing_direction"] = string(facing) if isinstance(facing, str) else integer(facing)
        primary[index] = len(palette)
        palette.append(compound({
            "name": string("minecraft:" + suffix), "states": compound(states),
            "version": integer(18168865),
        }))
        if condition_mode is not OMIT:
            actor = {
                "id": string("CommandBlock"), "x": integer(x + 400),
                "y": integer(y + 70), "z": integer(z - 800),
                "conditionalMode": byte(condition_mode), "auto": byte(0),
                "TickDelay": integer(0), "ExecuteOnFirstTick": byte(1),
            }
            if command is not OMIT:
                actor["Command"] = string(command)
            positions[str(index)] = compound({"block_entity_data": compound(actor)})
    if first_index is not None:
        primary[0] = first_index
    layers = (list_tag(11, (int_array(primary),)) if version == 2 else
              list_tag(9, (list_tag(3, map(integer, layer))
                          for layer in (primary, [-1] * volume))))
    structure = compound({
        "block_indices": layers,
        "entities": list_tag(10, ()),
        "palette": compound({"default": compound({
            "block_palette": list_tag(10, palette),
            "block_position_data": compound(positions),
        })}),
    })
    fields = {
        "format_version": integer(version),
        "size": list_tag(3, map(integer, size)),
        "structure_world_origin": list_tag(3, map(integer, (400, 70, -800))),
        "structure": structure if encode_structure is None else encode_structure(structure),
    }
    if compression_tag is not OMIT:
        fields["compression"] = compression_tag
    root = compound(fields)
    return bytes([root[0]]) + string_bytes("") + root[1]


def make_compressed(blocks, *, inner_transform=lambda nbt: nbt,
                    stream_transform=lambda stream: stream):
    def compressed_structure(value):
        kind, payload = value
        inner = bytes([kind]) + string_bytes("") + payload
        return byte_array(stream_transform(zlib.compress(inner_transform(inner))))

    return make_structure(blocks, version=2, compression_tag=integer(1),
                          encode_structure=compressed_structure)


SAMPLE_COMMAND = "say synthetic_command_BODY_876541"
CLEAN = (((2, 1, 1), "command_block", 5, 0, 0, SAMPLE_COMMAND),)
FINDINGS = (
    ((2, 0, 1), "chain_command_block", 2, 1, 0, SAMPLE_COMMAND),
    ((1, 1, 0), "repeating_command_block", 3, 0, 1, SAMPLE_COMMAND),
    ((0, 0, 1), "command_block", 6, 1, 1, OMIT),
    ((0, 1, 1), "command_block", "2", 0, 0, " \t"),
    ((2, 1, 0), "command_block", OMIT, 0, OMIT, OMIT),
)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m tests.make_fixtures OUTPUT_DIR")
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "clean.mcstructure").write_bytes(make_structure(CLEAN))
    (destination / "findings.mcstructure").write_bytes(make_structure(FINDINGS))
    (destination / "compressed-findings.mcstructure").write_bytes(make_compressed(FINDINGS))


if __name__ == "__main__":
    main()
