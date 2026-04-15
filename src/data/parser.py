import openpyxl

from ..utils.constants import (
    HEADER_COLUMNS, DETAIL_COLUMNS, PRODUCT_COLUMNS, NET_TOTAL_COLUMN,
)
from ..utils.helpers import (
    format_decimal, split_document, split_code_name, parse_field, cell_str,
)


def _load_rows(input_path):
    """Load all rows from the XLSX as a list of {column: value} dicts."""
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=False):
        cell_map = {c.column: c.value for c in row}
        rows.append(cell_map)
    return rows


def _parse_products(rows, i, total_rows):
    """Read product rows until 'Totais' or an empty row is found."""
    products = []
    while i < total_rows:
        prod_a = cell_str(rows[i], PRODUCT_COLUMNS['produto'])
        if prod_a in ('Totais', ''):
            break
        products.append({
            'produto': prod_a,
            'qtdade': rows[i].get(PRODUCT_COLUMNS['qtdade'], 0),
            'vl_unit': rows[i].get(PRODUCT_COLUMNS['vl_unit'], 0),
            'vl_total': rows[i].get(PRODUCT_COLUMNS['vl_total'], 0),
            'vl_desconto': rows[i].get(PRODUCT_COLUMNS['vl_desconto'], 0),
            'tot_liq': rows[i].get(PRODUCT_COLUMNS['tot_liq'], 0),
            'icms_ret': rows[i].get(PRODUCT_COLUMNS['icms_ret'], 0),
        })
        i += 1
    return products, i


def _build_record(doc_type, doc_number, header, product):
    """Build a final record dict from header data + a single product."""
    prod_code, prod_name = split_code_name(product['produto'])
    return {
        'doc_tipo': doc_type,
        'doc_numero': doc_number,
        'pagamento': header['pagamento'],
        'emissao': header['emissao'],
        'operador': header['operador'],
        'cliente_cod': header['cliente_cod'],
        'cliente_nome': header['cliente_nome'],
        'empresa': header['empresa'],
        'vendedor': header['vendedor'],
        'obs': header['obs'],
        'produto_cod': prod_code,
        'produto_nome': prod_name,
        'qtdade': format_decimal(product['qtdade']),
        'vl_unit': format_decimal(product['vl_unit']),
        'vl_total': format_decimal(product['vl_total']),
        'vl_desconto': format_decimal(product['vl_desconto']),
        'tot_liq': format_decimal(product['tot_liq']),
        'icms_ret': format_decimal(product['icms_ret']),
        'total_liquido_doc': format_decimal(header['total_liquido_doc']),
    }


def parse_xlsx(input_path):
    """Parse an accounts-receivable XLSX and return (records, skipped)."""
    rows = _load_rows(input_path)
    total_rows = len(rows)

    records = []
    skipped = []
    i = 0

    while i < total_rows:
        cell_a = cell_str(rows[i], 1)

        if not cell_a.startswith('Documento:'):
            i += 1
            continue

        start_line = i + 1
        try:
            # --- Document header ---
            document = parse_field(cell_a, 'Documento:')
            payment = parse_field(cell_str(rows[i], HEADER_COLUMNS['pagamento']), 'Pagto:')
            issue_date = parse_field(cell_str(rows[i], HEADER_COLUMNS['emissao']), 'Emissão:')
            operator = parse_field(cell_str(rows[i], HEADER_COLUMNS['operador']), 'Operador:')

            # --- Client ---
            i += 1
            client_raw = cell_str(rows[i], DETAIL_COLUMNS['cliente'])
            client = parse_field(client_raw, 'Cliente:')
            if client is None:
                raise ValueError(f"Expected 'Cliente:' at line {i+1}, found: '{client_raw}'")
            client_code, client_name = split_code_name(client)

            # --- Company / Salesperson ---
            i += 1
            company = parse_field(cell_str(rows[i], DETAIL_COLUMNS['empresa']), 'Empresa:')
            salesperson = parse_field(cell_str(rows[i], DETAIL_COLUMNS['vendedor']), 'Vendedor:')

            # --- Notes ---
            i += 1
            notes = parse_field(cell_str(rows[i], DETAIL_COLUMNS['obs']), 'Obs:') or ''

            # --- Skip to "Produto" header row ---
            i += 1
            cell_check = cell_str(rows[i], 1)
            if cell_check == '':
                i += 1
                cell_check = cell_str(rows[i], 1)
            if cell_check != 'Produto':
                raise ValueError(f"Expected 'Produto' at line {i+1}, found: '{cell_check}'")

            # --- Products ---
            i += 1
            products, i = _parse_products(rows, i, total_rows)

            # --- Totals ---
            if cell_str(rows[i], 1) != 'Totais':
                i += 1
            i += 2
            net_total = rows[i].get(NET_TOTAL_COLUMN, 0)

            doc_type, doc_number = split_document(document)

            header = {
                'pagamento': payment,
                'emissao': issue_date,
                'operador': operator,
                'cliente_cod': client_code,
                'cliente_nome': client_name,
                'empresa': company,
                'vendedor': salesperson,
                'obs': notes,
                'total_liquido_doc': net_total,
            }

            for product in products:
                records.append(_build_record(doc_type, doc_number, header, product))

            i += 1

        except Exception as e:
            skipped.append({
                'line': start_line,
                'reason': str(e),
                'content': cell_a,
            })
            i += 1

    return records, skipped