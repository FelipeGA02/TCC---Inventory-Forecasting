# Abre o DOCX no Word (automação COM) e exporta PDF, para conferir a paginação da ata.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File exportar_pdf.ps1 -In <ata.docx> -OutPdf <ata.pdf>
#
# Use caminhos Windows absolutos. Imprime o número de páginas (as atas 02–04 têm 5).
# Se o Word já estiver aberto, reaproveita a instância e fecha só o documento que abriu.
param([string]$In, [string]$OutPdf)
$word = New-Object -ComObject Word.Application
$preexisting = $word.Documents.Count
if ($preexisting -eq 0) { $word.Visible = $false }
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($In, $false, $true, $false)
  $doc.Repaginate()
  "paginas: " + $doc.ComputeStatistics(2)
  $doc.ExportAsFixedFormat($OutPdf, 17)   # 17 = wdExportFormatPDF
  $doc.Close($false)
} finally {
  if ($preexisting -eq 0) { $word.Quit() }
}
