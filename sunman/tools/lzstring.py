"""LZ-String decompressFromUTF16 — enough of it to open a Blockbench backup.

Blockbench writes its autosave backups as the literal marker `<lz>` followed by an LZ-String
`compressToUTF16` payload (characters in codepoints 32..16415). Nothing on this machine could
read them, and the backups were the only surviving copy of the Sun Man skeleton, so this is a
direct port of the reference `_decompress` routine.
"""


def _decompress(length, reset_value, get_next):
    dictionary = {i: i for i in range(3)}
    enlarge_in = 4
    dict_size = 4
    num_bits = 3
    result = []

    data_val = get_next(0)
    data_position = reset_value
    data_index = 1

    def read(nbits):
        nonlocal data_val, data_position, data_index
        bits = 0
        maxpower = 1 << nbits
        power = 1
        while power != maxpower:
            resb = data_val & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_val = get_next(data_index)
                data_index += 1
            bits |= (1 if resb > 0 else 0) * power
            power <<= 1
        return bits

    nxt = read(2)
    if nxt == 0:
        c = chr(read(8))
    elif nxt == 1:
        c = chr(read(16))
    else:
        return ""

    dictionary[3] = c
    w = c
    result.append(c)

    while True:
        if data_index > length:
            return ""
        c = read(num_bits)
        if c == 0:
            dictionary[dict_size] = chr(read(8))
            dict_size += 1
            c = dict_size - 1
            enlarge_in -= 1
        elif c == 1:
            dictionary[dict_size] = chr(read(16))
            dict_size += 1
            c = dict_size - 1
            enlarge_in -= 1
        elif c == 2:
            return "".join(result)

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1

        if c in dictionary:
            entry = dictionary[c]
        elif c == dict_size:
            entry = w + w[0]
        else:
            return None

        result.append(entry)
        dictionary[dict_size] = w + entry[0]
        dict_size += 1
        enlarge_in -= 1
        w = entry

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1


def decompress(compressed):
    """Plain LZString.compress output: raw 16-bit chars, no +32 offset."""
    if not compressed:
        return ""
    return _decompress(len(compressed), 32768, lambda i: ord(compressed[i]))


def decompress_from_utf16(compressed):
    if compressed is None or compressed == "":
        return ""
    return _decompress(len(compressed), 16384,
                       lambda i: ord(compressed[i]) - 32)


def read_bbmodel(path):
    """Open a .bbmodel whether it is plain JSON or an `<lz>` backup."""
    import json
    raw = open(path, encoding="utf-8").read()
    if raw.startswith("<lz>"):
        body = raw[4:]
        # Blockbench uses plain LZString.compress (16-bit chars); the UTF-16 variant is
        # offset by 32 and caps at 16415, which this payload exceeds.
        raw = decompress(body) or decompress_from_utf16(body)
    return json.loads(raw)


if __name__ == "__main__":
    import sys
    d = read_bbmodel(sys.argv[1])
    print("elements:", len(d.get("elements", [])))
    print("outliner roots:", len(d.get("outliner", [])))
    print("resolution:", d.get("resolution"))
