# Abre o DOCX no Word (automação COM), atualiza os números de página do sumário e dos campos
# PAGEREF fora dele (capítulos 10, 11 e Referências), salva um DOCX "salvo pelo Word" e exporta PDF.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File word_finalize.ps1 -In <draft.docx> -OutDocx <final.docx> -OutPdf <final.pdf>
#
# Use caminhos Windows absolutos. O DOCX entregue deve ser o -OutDocx (números de página corretos).
# Se o usuário estiver com o Word aberto, a automação pode reutilizar a mesma instância: nesse caso
# o script fecha só o documento que abriu e não encerra o Word.
param([string]$In, [string]$OutDocx, [string]$OutPdf)
$word = New-Object -ComObject Word.Application
$preexisting = $word.Documents.Count
if ($preexisting -eq 0) { $word.Visible = $false }
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($In, $false, $false, $false)
  for ($pass = 0; $pass -lt 2; $pass++) {
    $doc.Repaginate()
    if ($doc.TablesOfContents.Count -ge 1) { $doc.TablesOfContents.Item(1).UpdatePageNumbers() | Out-Null }
    foreach ($f in $doc.Fields) { if ($f.Type -eq 37) { $f.Update() | Out-Null } }  # 37 = wdFieldPageRef
  }
  "pages: " + $doc.ComputeStatistics(2)
  $doc.SaveAs2($OutDocx, 16)          # 16 = wdFormatXMLDocument
  if ($OutPdf) { $doc.ExportAsFixedFormat($OutPdf, 17) }  # 17 = wdExportFormatPDF
  $doc.Close($false)
} finally {
  if ($preexisting -eq 0) { $word.Quit() }
}
