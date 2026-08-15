class HexCrossword:
    # default function makes an empty cell from r and c
    def __init__(self, default):
        self.grid = {}
        self.default = default

    def row_len(self, r):
        return 13 - abs(r - 6)

    def get_lines_for_cell(self, r, c):
        offset = max(0, r - 6)
        return {"a": c + offset, "b": r - c + 6 - offset, "c": r}

    # copied from the original site pretty much
    def get_line(self, axis, num):
        coords = []
        if axis == "c":
            coords = [(num, c) for c in range(self.row_len(num))]
        elif axis == "a":
            coords = [(r, num - max(0, r - 6)) for r in range(13)]
        elif axis == "b":
            coords = [(r, r + 6 - max(0, r - 6) - num) for r in range(12, -1, -1)]

        line = []
        for r, c in coords:
            if 0 <= c < self.row_len(r):
                if not (r, c) in self.grid:
                    self.grid[(r, c)] = self.default(r, c)
                line.append(self.grid[(r, c)])
        return line
