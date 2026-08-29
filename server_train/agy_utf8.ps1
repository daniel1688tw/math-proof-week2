param(
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][int]$TimeoutSeconds
)
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$promptBase64 = [Console]::In.ReadToEnd().Trim()
$promptText = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String($promptBase64)
)
$responseText = ($promptText | & agy --model $Model --effort medium `
    --disable-slash-commands --print-timeout "${TimeoutSeconds}s" `
    2>&1 | Out-String)
$agyExit = $LASTEXITCODE
$responseBase64 = [System.Convert]::ToBase64String(
    [System.Text.Encoding]::UTF8.GetBytes($responseText)
)
[Console]::Out.Write($responseBase64)
exit $agyExit
