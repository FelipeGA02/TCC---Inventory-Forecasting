/**
 * Exportação de tabelas no navegador: CSV (padrão Excel pt-BR), XLSX e impressão (PDF).
 *
 * O XLSX é montado à mão (zip sem compressão + SpreadsheetML mínimo) para não trazer uma
 * dependência só para isso. Quando a API estiver conectada, os relatórios oficiais vêm de
 * `/api/v1/export/*` (openpyxl/reportlab no backend).
 */

export type TipoColuna = "texto" | "numero" | "decimal" | "data";

export interface Coluna {
  titulo: string;
  tipo: TipoColuna;
}

export type Celula = string | number | null;

export interface Tabela {
  colunas: Coluna[];
  linhas: Celula[][];
}

function baixarBlob(blob: Blob, nomeArquivo: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------------------------------------------------------------------
// CSV
// ---------------------------------------------------------------------------

function celulaCsv(valor: Celula, tipo: TipoColuna): string {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") {
    const casas = tipo === "decimal" ? 2 : tipo === "numero" ? 1 : 0;
    const txt = Number.isInteger(valor) ? String(valor) : valor.toFixed(casas).replace(/\.?0+$/, "");
    return txt.replace(".", ",");
  }
  if (tipo === "data" && /^\d{4}-\d{2}-\d{2}/.test(valor)) {
    const [a, m, d] = valor.slice(0, 10).split("-");
    return `${d}/${m}/${a}`;
  }
  return /[;"\n]/.test(valor) ? `"${valor.replace(/"/g, '""')}"` : valor;
}

export function gerarCsv(tabela: Tabela): string {
  const cab = tabela.colunas.map((c) => celulaCsv(c.titulo, "texto")).join(";");
  const corpo = tabela.linhas.map((l) => l.map((v, i) => celulaCsv(v, tabela.colunas[i]?.tipo ?? "texto")).join(";"));
  return [cab, ...corpo].join("\r\n");
}

export function baixarCsv(tabela: Tabela, nomeArquivo: string): number {
  // BOM para o Excel reconhecer UTF-8 (acentos) ao abrir com duplo clique.
  const blob = new Blob(["﻿" + gerarCsv(tabela)], { type: "text/csv;charset=utf-8" });
  baixarBlob(blob, `${nomeArquivo}.csv`);
  return blob.size;
}

// ---------------------------------------------------------------------------
// XLSX
// ---------------------------------------------------------------------------

const CRC_TABELA = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(dados: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < dados.length; i++) c = CRC_TABELA[(c ^ dados[i]!) & 0xff]! ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** Zip "stored" (sem compressão) — suficiente e aceito pelo Excel/LibreOffice. */
function zip(arquivos: { nome: string; conteudo: string }[]): Blob {
  const enc = new TextEncoder();
  const partes: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;

  for (const arq of arquivos) {
    const nome = enc.encode(arq.nome);
    const dados = enc.encode(arq.conteudo);
    const crc = crc32(dados);

    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(4, 20, true);
    local.setUint16(6, 0x0800, true); // nomes em UTF-8
    local.setUint16(8, 0, true);
    local.setUint32(14, crc, true);
    local.setUint32(18, dados.length, true);
    local.setUint32(22, dados.length, true);
    local.setUint16(26, nome.length, true);
    partes.push(new Uint8Array(local.buffer), nome, dados);

    const cd = new DataView(new ArrayBuffer(46));
    cd.setUint32(0, 0x02014b50, true);
    cd.setUint16(4, 20, true);
    cd.setUint16(6, 20, true);
    cd.setUint16(8, 0x0800, true);
    cd.setUint32(16, crc, true);
    cd.setUint32(20, dados.length, true);
    cd.setUint32(24, dados.length, true);
    cd.setUint16(28, nome.length, true);
    cd.setUint32(42, offset, true);
    central.push(new Uint8Array(cd.buffer), nome);

    offset += 30 + nome.length + dados.length;
  }

  const tamCentral = central.reduce((s, p) => s + p.length, 0);
  const fim = new DataView(new ArrayBuffer(22));
  fim.setUint32(0, 0x06054b50, true);
  fim.setUint16(8, arquivos.length, true);
  fim.setUint16(10, arquivos.length, true);
  fim.setUint32(12, tamCentral, true);
  fim.setUint32(16, offset, true);

  return new Blob([...partes, ...central, new Uint8Array(fim.buffer)] as BlobPart[], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

const xmlEsc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function letraColuna(i: number): string {
  let s = "";
  let n = i + 1;
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

/** Data ISO → número serial do Excel (dias desde 1899-12-30). */
function serialExcel(iso: string): number {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Math.round((Date.UTC(a!, m! - 1, d!) - Date.UTC(1899, 11, 30)) / 86400000);
}

// estilos: 0 normal · 1 cabeçalho · 2 data · 3 inteiro com milhar · 4 decimal
const ESTILO: Record<TipoColuna, number> = { texto: 0, data: 2, numero: 3, decimal: 4 };

function planilha(tabela: Tabela): string {
  const larguras = tabela.colunas.map((c, i) => {
    const maior = Math.max(c.titulo.length, ...tabela.linhas.slice(0, 200).map((l) => String(l[i] ?? "").length));
    return Math.min(60, Math.max(10, maior + 2));
  });
  const cols = larguras.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join("");

  const linha = (r: number, celulas: string[]) => `<row r="${r}">${celulas.join("")}</row>`;
  const cab = linha(
    1,
    tabela.colunas.map((c, i) => `<c r="${letraColuna(i)}1" t="inlineStr" s="1"><is><t>${xmlEsc(c.titulo)}</t></is></c>`),
  );
  const corpo = tabela.linhas.map((l, j) => {
    const r = j + 2;
    return linha(
      r,
      l.map((v, i) => {
        const ref = `${letraColuna(i)}${r}`;
        const tipo = tabela.colunas[i]?.tipo ?? "texto";
        if (v === null || v === "") return `<c r="${ref}"/>`;
        if (tipo === "data" && typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v))
          return `<c r="${ref}" s="2"><v>${serialExcel(v)}</v></c>`;
        if (typeof v === "number") return `<c r="${ref}" s="${ESTILO[tipo]}"><v>${v}</v></c>`;
        return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xmlEsc(String(v))}</t></is></c>`;
      }),
    );
  });

  return (
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>` +
    `<cols>${cols}</cols><sheetData>${cab}${corpo.join("")}</sheetData>` +
    `<autoFilter ref="A1:${letraColuna(tabela.colunas.length - 1)}${tabela.linhas.length + 1}"/>` +
    `</worksheet>`
  );
}

const ESTILOS_XML =
  `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
  `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
  `<numFmts count="2"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/><numFmt numFmtId="165" formatCode="#,##0.0"/></numFmts>` +
  `<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>` +
  `<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>` +
  `<fill><patternFill patternType="solid"><fgColor rgb="FF1A6B3C"/><bgColor indexed="64"/></patternFill></fill></fills>` +
  `<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>` +
  `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
  `<cellXfs count="5">` +
  `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
  `<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
  `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
  `<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
  `<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
  `</cellXfs></styleSheet>`;

export function baixarXlsx(tabela: Tabela, nomeArquivo: string, nomeAba = "Dados"): number {
  const aba = xmlEsc(nomeAba.replace(/[\\/?*[\]:]/g, " ").slice(0, 31));
  const blob = zip([
    {
      nome: "[Content_Types].xml",
      conteudo:
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
        `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
        `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
        `<Default Extension="xml" ContentType="application/xml"/>` +
        `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
        `<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>` +
        `<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>` +
        `</Types>`,
    },
    {
      nome: "_rels/.rels",
      conteudo:
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
        `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
        `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
        `</Relationships>`,
    },
    {
      nome: "xl/workbook.xml",
      conteudo:
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
        `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
        `<sheets><sheet name="${aba}" sheetId="1" r:id="rId1"/></sheets></workbook>`,
    },
    {
      nome: "xl/_rels/workbook.xml.rels",
      conteudo:
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
        `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
        `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>` +
        `<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
        `</Relationships>`,
    },
    { nome: "xl/styles.xml", conteudo: ESTILOS_XML },
    { nome: "xl/worksheets/sheet1.xml", conteudo: planilha(tabela) },
  ]);
  baixarBlob(blob, `${nomeArquivo}.xlsx`);
  return blob.size;
}

// ---------------------------------------------------------------------------
// PDF (via impressão do navegador)
// ---------------------------------------------------------------------------

/** Abre o HTML numa janela e chama a impressão — o usuário escolhe "Salvar como PDF". */
export function imprimirHtml(html: string): boolean {
  const janela = window.open("", "_blank", "width=1000,height=800");
  if (!janela) return false;
  janela.document.open();
  janela.document.write(html);
  janela.document.close();
  let impresso = false;
  const imprimir = () => {
    if (impresso || janela.closed) return;
    impresso = true;
    janela.focus();
    janela.print();
  };
  janela.onload = imprimir;
  // Alguns navegadores não disparam onload para documentos escritos via document.write.
  setTimeout(imprimir, 600);
  return true;
}

export function tabelaHtml(tabela: Tabela, formatar: (v: Celula, tipo: TipoColuna) => string): string {
  const th = tabela.colunas.map((c) => `<th class="${c.tipo === "texto" || c.tipo === "data" ? "" : "num"}">${xmlEsc(c.titulo)}</th>`).join("");
  const trs = tabela.linhas
    .map(
      (l) =>
        `<tr>${l
          .map((v, i) => {
            const tipo = tabela.colunas[i]?.tipo ?? "texto";
            return `<td class="${tipo === "texto" || tipo === "data" ? "" : "num"}">${xmlEsc(formatar(v, tipo))}</td>`;
          })
          .join("")}</tr>`,
    )
    .join("");
  return `<table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table>`;
}
