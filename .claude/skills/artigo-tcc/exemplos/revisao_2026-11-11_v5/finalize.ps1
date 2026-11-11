param([string]$In, [string]$OutDocx, [string]$OutPdf)
$word = New-Object -ComObject Word.Application
$pre = $word.Documents.Count
if ($pre -eq 0) { $word.Visible = $false }
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($In, $false, $false, $false)
  for ($pass = 0; $pass -lt 2; $pass++) {
    $doc.Repaginate()
    if ($doc.TablesOfContents.Count -ge 1) { $doc.TablesOfContents.Item(1).Update() | Out-Null }
  }
  "pages: " + $doc.ComputeStatistics(2)
  $doc.SaveAs2($OutDocx, 16)
  if ($OutPdf) { $doc.ExportAsFixedFormat($OutPdf, 17) }
  $doc.Close($false)
} finally { if ($pre -eq 0) { $word.Quit() } }
