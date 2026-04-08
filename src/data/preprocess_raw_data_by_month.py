import openpyxl
import csv
import os
import json
import hashlib
from datetime import datetime

RAW_DIR = 'data/raw'
PROCESSED_DIR = 'data/processed'
OUTPUT_CSV = os.path.join(PROCESSED_DIR, 'contas_a_receber.csv')
CONTROL_FILE = os.path.join(PROCESSED_DIR, '.processados.json')

CAMPOS = [
    'documento', 'pagamento', 'emissao', 'operador', 'cliente',
    'empresa', 'vendedor', 'obs', 'produto', 'qtdade', 'vl_unit',
    'vl_total', 'vl_desconto', 'tot_liq', 'icms_ret', 'total_liquido_doc',
    'arquivo_origem',
]

def file_hash(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_control():
    if os.path.exists(CONTROL_FILE):
        with open(CONTROL_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_control(control):
    with open(CONTROL_FILE, 'w') as f:
        json.dump(control, f, indent=2, ensure_ascii=False)


def parse_field(text, prefix):
    if text and text.strip().startswith(prefix):
        return text.strip()[len(prefix):].strip()
    return None


def parse_xlsx(input_path):
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active

    rows = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column, values_only=False):
        cell_map = {}
        for c in row:
            cell_map[c.column] = c.value
        rows.append(cell_map)

    registros = []
    ignorados = []
    i = 0
    total_rows = len(rows)

    while i < total_rows:
        cell_a = str(rows[i].get(1, '') or '').strip()

        if not cell_a.startswith('Documento:'):
            i += 1
            continue

        linha_inicio = i + 1
        try:
            documento = parse_field(cell_a, 'Documento:')
            pagamento = parse_field(str(rows[i].get(3, '') or '').strip(), 'Pagto:')
            emissao = parse_field(str(rows[i].get(8, '') or '').strip(), 'Emissão:')
            operador = parse_field(str(rows[i].get(17, '') or '').strip(), 'Operador:')

            i += 1
            cliente_raw = str(rows[i].get(1, '') or '').strip()
            cliente = parse_field(cliente_raw, 'Cliente:')
            if cliente is None:
                raise ValueError(f"Esperado 'Cliente:' na linha {i+1}, encontrado: '{cliente_raw}'")

            i += 1
            empresa = parse_field(str(rows[i].get(1, '') or '').strip(), 'Empresa:')
            vendedor = parse_field(str(rows[i].get(13, '') or '').strip(), 'Vendedor:')

            i += 1
            obs = parse_field(str(rows[i].get(1, '') or '').strip(), 'Obs:') or ''

            i += 1
            cell_check = str(rows[i].get(1, '') or '').strip()
            if cell_check == '':
                i += 1
                cell_check = str(rows[i].get(1, '') or '').strip()

            if cell_check != 'Produto':
                raise ValueError(f"Esperado 'Produto' na linha {i+1}, encontrado: '{cell_check}'")

            i += 1
            produtos = []
            while i < total_rows:
                prod_a = str(rows[i].get(1, '') or '').strip()
                if prod_a in ('Totais', ''):
                    break
                produtos.append({
                    'produto': prod_a,
                    'qtdade': rows[i].get(8, 0),
                    'vl_unit': rows[i].get(9, 0),
                    'vl_total': rows[i].get(14, 0),
                    'vl_desconto': rows[i].get(15, 0),
                    'tot_liq': rows[i].get(18, 0),
                    'icms_ret': rows[i].get(20, 0),
                })
                i += 1

            if str(rows[i].get(1, '') or '').strip() != 'Totais':
                i += 1

            i += 1  
            i += 1  
            total_liquido = rows[i].get(5, 0)

            for prod in produtos:
                reg = {
                    'documento': documento,
                    'pagamento': pagamento,
                    'emissao': emissao,
                    'operador': operador,
                    'cliente': cliente,
                    'empresa': empresa,
                    'vendedor': vendedor,
                    'obs': obs,
                    'total_liquido_doc': total_liquido,
                }
                reg.update(prod)
                registros.append(reg)

            i += 1

        except Exception as e:
            ignorados.append({
                'linha': linha_inicio,
                'motivo': str(e),
                'conteudo': cell_a,
            })
            i += 1

    return registros, ignorados


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    control = load_control()

    arquivos = sorted([
        f for f in os.listdir(RAW_DIR)
        if f.lower().endswith(('.xlsx', '.xlsm'))
    ])

    if not arquivos:
        print('Nenhum arquivo .xlsx encontrado em data/raw/')
        return

    novos = []
    for arq in arquivos:
        path = os.path.join(RAW_DIR, arq)
        h = file_hash(path)
        registro_ctrl = control.get(arq)
        if registro_ctrl and registro_ctrl.get('hash') == h:
            continue
        novos.append((arq, path, h))

    if not novos:
        print('Todos os arquivos já foram processados. Nenhuma novidade.')
        return

    print(f'{len(novos)} arquivo(s) novo(s) para processar.\n')

    csv_existe = os.path.exists(OUTPUT_CSV)
    total_registros = 0
    total_ignorados = 0

    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=';')
        if not csv_existe:
            writer.writeheader()

        for arq, path, h in novos:
            print(f'Processando: {arq}')
            registros, ignorados = parse_xlsx(path)

            for reg in registros:
                reg['arquivo_origem'] = arq
                writer.writerow(reg)

            total_registros += len(registros)
            total_ignorados += len(ignorados)

            if ignorados:
                print(f'  [!] {len(ignorados)} registro(s) ignorado(s):')
                for ig in ignorados:
                    print(f'    Linha {ig["linha"]}: {ig["motivo"]}')
                    print(f'      Conteúdo: {ig["conteudo"]}')
            else:
                print(f'  [OK] {len(registros)} linhas extraidas, sem erros.')

            control[arq] = {
                'hash': h,
                'processado_em': datetime.now().isoformat(),
                'registros': len(registros),
                'ignorados': len(ignorados),
            }

    save_control(control)
    print(f'\nResumo: {total_registros} linhas adicionadas, {total_ignorados} ignoradas.')
    print(f'CSV: {OUTPUT_CSV}')


if __name__ == '__main__':
    main()