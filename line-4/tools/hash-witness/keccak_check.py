"""Second Keccak-256 implementation: matrix lanes and generated round constants.

Written for this tool from the permutation specification, not imported from the
ancestor encoder. Ethereum's suffix is 0x01, not SHA3-256's 0x06.
"""

MASK64 = (1 << 64) - 1


def rotate(lane, amount):
    amount %= 64
    return ((lane << amount) | (lane >> ((64 - amount) % 64))) & MASK64


def permute(a):
    lfsr = 1
    for _ in range(24):
        columns = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4]
                   for x in range(5)]
        for x in range(5):
            delta = columns[(x - 1) % 5] ^ rotate(columns[(x + 1) % 5], 1)
            for y in range(5):
                a[x][y] ^= delta
        # Follow the 24 non-origin lanes in place; no rotation lookup table.
        x, y, carried = 1, 0, a[1][0]
        for step in range(24):
            x, y = y, (2 * x + 3 * y) % 5
            carried, a[x][y] = a[x][y], rotate(carried, (step + 1) * (step + 2) // 2)
        for y in range(5):
            row = [a[x][y] for x in range(5)]
            for x in range(5):
                a[x][y] = row[x] ^ ((~row[(x + 1) % 5]) & row[(x + 2) % 5])
        # Seven LFSR steps generate each iota constant, low bit first.
        for bit in range(7):
            if lfsr & 1:
                a[0][0] ^= 1 << ((1 << bit) - 1)
            lfsr = ((lfsr << 1) ^ (0x71 if lfsr & 0x80 else 0)) & 0xff


def _sponge(message, suffix):
    if type(message) is not bytes:
        raise ValueError('Keccak input must be bytes')
    rate = 136
    tail = bytearray(message)
    tail.extend(bytes(rate - len(tail) % rate))
    tail[len(message)] = suffix
    tail[-1] |= 0x80
    state = [[0] * 5 for _ in range(5)]
    for start in range(0, len(tail), rate):
        for lane in range(17):
            position = start + 8 * lane
            state[lane % 5][lane // 5] ^= int.from_bytes(tail[position:position + 8], 'little')
        permute(state)
    return b''.join(state[x][0].to_bytes(8, 'little') for x in range(4))


def keccak256(message):
    return _sponge(message, 0x01)
