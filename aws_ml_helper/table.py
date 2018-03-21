__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '21 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'


STYLES = {
    'plain': {
        'corner': '',
        'top': '',
        'top_filler': '',
        'header': '-',
        'header_filler': ' ',
        'bottom': '',
        'bottom_filler': '',
        'vertical': '',
    },
    'psql': {
        'corner': '+',
        'top': '-',
        'top_filler': '-',
        'header': '-',
        'header_filler': '-',
        'bottom': '-',
        'bottom_filler': '-',
        'vertical': '|'
    }
}


def format_row(row, cols, style):
    vertical = style['vertical']
    s = ''
    for i, item in enumerate(row):
        if i == 0:
            s += vertical
        s += f' {item.ljust(cols[i])} {vertical}'
    return s + '\n'


def hbar(cols, type, style):
    """Creates a horizontal line.

    Args:
        cols: Columns specification
        type: top|header|bottom
        style: Style dictioncary
    """
    s = ''
    el = style[type]
    filler = style[f'{type}_filler']
    corner = style['corner']
    for i, length in enumerate(cols):
        if i == 0:
            s += corner
        s += f'{filler}{el * length}{filler}{corner}'
    if s.strip() == '':
        return ''
    return s + '\n'


def table(data, headers=None, style='psql'):
    """Format data as table

    Args:
        data (list of list): Table data. Outer list contains rows.
        headers (list of str): Column headers
        style (str): Table style

    Returns:
        str: Formatted data as a string
    """
    if len(data) == 0:
        return ''

    # Convert all elements to strings
    data = [[str(col) for col in row] for row in data]

    if headers:
        ncols = len(headers)
        cols = [len(col) for col in headers]
    else:
        ncols = len(data[0])
        cols = [0] * ncols

    for i in range(len(data)):
        for j in range(ncols):
            cols[j] = max(cols[j], len(data[i][j]))

    style = STYLES[style]

    s = hbar(cols, 'top', style)
    if headers:
        s += format_row(headers, cols, style)
        s += hbar(cols, 'header', style)

    for row in data:
        s += format_row(row, cols, style)

    s += hbar(cols, 'bottom', style)
    return s
