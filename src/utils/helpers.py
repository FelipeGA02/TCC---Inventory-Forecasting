import hashlib
import json
import os

def format_decimal(value):
    """Format a numeric value using comma as the decimal separator."""
    if value is None:
        return '0'
    try:
        num = float(value)
        if num == int(num):
            return str(int(num))
        return f'{num:.2f}'.replace('.', ',')
    except (ValueError, TypeError):
        return str(value).replace('.', ',')


def split_document(text):
    """Split a document string like 'C1 44799' into (type, number)."""
    if not text:
        return '', ''
    parts = text.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return '', text.strip()


def split_code_name(text):
    """Split 'code - name' into (code, name). E.g. '2820 - TATIANE' -> ('2820', 'TATIANE')."""
    if not text:
        return '', ''
    if ' - ' in text:
        code, name = text.split(' - ', 1)
        return code.strip(), name.strip()
    return '', text.strip()


def parse_field(text, prefix):
    """Extract the value after a prefix. E.g. parse_field('Cliente: João', 'Cliente:') -> 'João'."""
    if text and text.strip().startswith(prefix):
        return text.strip()[len(prefix):].strip()
    return None


def file_hash(path):
    """Calculate the MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_control(control_file):
    """Load the processing control file."""
    if os.path.exists(control_file):
        with open(control_file, 'r') as f:
            return json.load(f)
    return {}


def save_control(control, control_file):
    """Save the processing control file."""
    with open(control_file, 'w') as f:
        json.dump(control, f, indent=2, ensure_ascii=False)


def cell_str(row_map, col):
    """Extract a cell value as a cleaned string."""
    return str(row_map.get(col, '') or '').strip()