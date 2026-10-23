from dataclasses import dataclass

COLS = 6
ROWS = 4
HALF_GAP = 2.2
COL_STAGGER = (0.30, 0.30, 0.12, 0.0, 0.12, 0.22)
LEFT_THUMBS = ((3.9, 4.45), (5.0, 4.65))
TOTAL_WIDTH = COLS * 2 + HALF_GAP
TOTAL_HEIGHT = 5.65


@dataclass(frozen=True)
class Slot:
    index: int
    x: float
    y: float


def _mirror(x: float) -> float:
    return TOTAL_WIDTH - 1.0 - x


def slots(swap_thumbs: bool = False) -> list[Slot]:
    out: list[Slot] = []
    for index in range(ROWS * COLS):
        row, col = divmod(index, COLS)
        out.append(Slot(index, float(col), row + COL_STAGGER[col]))

    left_thumbs = list(LEFT_THUMBS)
    if swap_thumbs:
        left_thumbs = [(left_thumbs[1][0], left_thumbs[0][1]), (left_thumbs[0][0], left_thumbs[1][1])]
    out.append(Slot(24, left_thumbs[0][0], left_thumbs[0][1]))
    out.append(Slot(25, left_thumbs[1][0], left_thumbs[1][1]))

    right_stagger = tuple(reversed(COL_STAGGER))
    for offset in range(ROWS * COLS):
        row, col = divmod(offset, COLS)
        x = COLS + HALF_GAP + col
        out.append(Slot(26 + offset, x, row + right_stagger[col]))

    out.append(Slot(50, _mirror(left_thumbs[1][0]), left_thumbs[1][1]))
    out.append(Slot(51, _mirror(left_thumbs[0][0]), left_thumbs[0][1]))
    return out
