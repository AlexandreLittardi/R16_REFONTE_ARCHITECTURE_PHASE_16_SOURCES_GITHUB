"""Small, UI-independent spreadsheet edits for the project document.

The existing workbook JSON schema is preserved. Edits are in-place because
legacy views retain references to ``material_spreadsheet`` and ``cells``.
Validation is done before mutation; callers own the Undo/Redo transaction.
"""
import re


def cell_address(row, col):
    if not isinstance(row, int) or not isinstance(col, int) or row < 0 or col < 0:
        raise ValueError('Cell coordinates must be non-negative integers')
    n = col + 1
    letters = ''
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return f'{letters}{row + 1}'


def _in_bounds(state, row, col):
    return 0 <= row < state['rows'] and 0 <= col < state['cols']


def write_cell(state, row, col, value):
    """Set a raw cell value, returning True iff persisted content changes."""
    if not _in_bounds(state, row, col):
        raise ValueError('Cell is outside the current worksheet')
    address = cell_address(row, col)
    cells = state['cells']
    new = '' if value is None else str(value)
    old = cells.get(address, '')
    if old == new:
        return False
    if new:
        cells[address] = new
    else:
        cells.pop(address, None)
    return True


def paste_block(state, start_row, start_col, values):
    """Paste a rectangular or ragged block, clipping at worksheet bounds.

    An out-of-bounds starting cell is a no-op; non-string input is rejected
    before any workbook content is changed.
    """
    if not isinstance(start_row, int) or not isinstance(start_col, int):
        raise ValueError('Paste coordinates must be integers')
    if not isinstance(values, (list, tuple)) or any(not isinstance(r, (list, tuple)) for r in values):
        raise ValueError('Paste data must be a list of rows')
    for row in values:
        if any(not isinstance(item, str) for item in row):
            raise ValueError('Paste values must be strings')
    changed = False
    for dr, line in enumerate(values):
        for dc, value in enumerate(line):
            row, col = start_row + dr, start_col + dc
            if _in_bounds(state, row, col):
                changed = write_cell(state, row, col, value) or changed
    return changed


def append_axis(state, axis, limit):
    """Append one row/column if allowed. View redraw is left to the caller."""
    name = {'row': 'rows', 'col': 'cols'}[axis]
    if state[name] >= limit:
        return False
    state[name] += 1
    return True


def remove_last_axis(state, axis):
    """Trim final row/column and associated dimension metadata in-place.

    Caller handles the confirmation dialog when trimmed cells contain data.
    """
    name = {'row': 'rows', 'col': 'cols'}[axis]
    if state[name] <= 1:
        return False
    last = state[name] - 1
    if axis == 'row':
        for col in range(state['cols']):
            state['cells'].pop(cell_address(last, col), None)
        dimensions = state.get('row_heights', [])
    else:
        for row in range(state['rows']):
            state['cells'].pop(cell_address(row, last), None)
        dimensions = state.get('col_widths', [])
    state[name] -= 1
    if len(dimensions) > state[name]:
        del dimensions[state[name]:]
    return True


# Cell-fill calculations formerly performed inside the Tk mouse handler.
_REFERENCE = re.compile(r'(?<![A-Za-z_0-9])([A-Za-z]+)([1-9][0-9]*)(?![A-Za-z_0-9])')


def shift_formula(formula, dr, dc):
    """Move relative A1 references as in the original fill-handle action."""
    if not isinstance(formula, str) or not formula.startswith('='):
        return formula

    def shifted(match):
        idx = 0
        for letter in match.group(1).upper():
            idx = idx * 26 + ord(letter) - 64
        col = max(0, idx - 1 + dc)
        row = max(1, int(match.group(2)) + dr)
        return cell_address(row - 1, col)

    return _REFERENCE.sub(shifted, formula)


def fill_range(state, anchor, end, target):
    """Extend a selection, repeating raw values/formulas or a numeric series.

    Source values are snapshotted before any changes; the fill handle is one
    transaction irrespective of the number of populated destination cells.
    """
    r0, r1 = sorted((anchor[0], end[0]))
    c0, c1 = sorted((anchor[1], end[1]))
    rt, ct = target
    rows, cols = state['rows'], state['cols']
    if not (0 <= r0 <= r1 < rows and 0 <= c0 <= c1 < cols):
        raise ValueError('Selection is outside worksheet bounds')
    source = {(r, c): state['cells'].get(cell_address(r, c), '')
              for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
    vertical = r0 != r1 and c0 == c1
    horizontal = c0 != c1 and r0 == r1

    def numeric_pair(first, second):
        try:
            return float(first), float(second)
        except (ValueError, TypeError):
            return None

    changed = False
    for r in range(max(0, min(r0, rt)), min(rows, max(r1, rt) + 1)):
        for c in range(max(0, min(c0, ct)), min(cols, max(c1, ct) + 1)):
            if r0 <= r <= r1 and c0 <= c <= c1:
                continue
            sr = r0 + (r - r0) % (r1 - r0 + 1)
            sc = c0 + (c - c0) % (c1 - c0 + 1)
            raw = source[(sr, sc)]
            if vertical:
                pair = numeric_pair(source[(r0, c0)], source[(r0 + 1, c0)])
                if pair and r > r1:
                    raw = str(pair[0] + (pair[1] - pair[0]) * (r - r0))
            elif horizontal:
                pair = numeric_pair(source[(r0, c0)], source[(r0, c0 + 1)])
                if pair and c > c1:
                    raw = str(pair[0] + (pair[1] - pair[0]) * (c - c0))
            changed = write_cell(state, r, c, shift_formula(raw, r - sr, c - sc)) or changed
    return changed
