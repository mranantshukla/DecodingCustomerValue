# Adds workspace bin to PATH for current PowerShell session and defines helper functions to control automatic 'yes' behavior.
$bin = Join-Path $PSScriptRoot 'bin'
if (-not (Test-Path $bin)) { New-Item -ItemType Directory -Path $bin | Out-Null }
$env:PATH = "$bin;$env:PATH"

# Session flag to control auto-yes behavior. Default to true if not set.
if (-not (Test-Path variable:Global:AUTO_YES)) { Set-Variable -Name AUTO_YES -Value $true -Scope Global -Force }

function Enable-AutoYes { Set-Variable -Name AUTO_YES -Value $true -Scope Global -Force; Write-Output "AUTO_YES = true" }
function Disable-AutoYes { Set-Variable -Name AUTO_YES -Value $false -Scope Global -Force; Write-Output "AUTO_YES = false" }
function Toggle-AutoYes { Set-Variable -Name AUTO_YES -Value (-not $Global:AUTO_YES) -Scope Global -Force; Write-Output "AUTO_YES = $Global:AUTO_YES" }
function Get-AutoYesStatus { Write-Output "AUTO_YES = $Global:AUTO_YES" }

function ay { param([Parameter(ValueFromRemainingArguments=$true)] $args) $cmd = $args -join ' '; if ($Global:AUTO_YES) { bash -lic "yes | $cmd" } else { bash -lic "$cmd" } }

# Helper to decide whether to pipe 'yes' based on AUTO_YES
function Invoke-WithOptionalYes {
	param(
		[string] $Exe,
		[string] $Args
	)
	if ($Global:AUTO_YES) {
		$yesCmd = Join-Path $PSScriptRoot 'bin\\yes.cmd'
		& $yesCmd | & $Exe -ArgumentList $Args
	} else {
		& $Exe -ArgumentList $Args
	}
}

function bash {
	param([Parameter(ValueFromRemainingArguments=$true)] $args)
	$cmd = $args -join ' '
	if ($cmd -eq '') { & bash.exe } else { if ($Global:AUTO_YES) { & bash.exe -lic "yes | $cmd" } else { & bash.exe -lic "$cmd" } }
}

function sh {
	param([Parameter(ValueFromRemainingArguments=$true)] $args)
	$cmd = $args -join ' '
	if ($cmd -eq '') { & sh.exe } else { if ($Global:AUTO_YES) { & sh.exe -lic "yes | $cmd" } else { & sh.exe -lic "$cmd" } }
}

function wsl {
	param([Parameter(ValueFromRemainingArguments=$true)] $args)
	$cmd = $args -join ' '
	if ($cmd -eq '') { & wsl.exe } else { if ($Global:AUTO_YES) { & wsl.exe bash -lic "yes | $cmd" } else { & wsl.exe bash -lic "$cmd" } }
}

function python {
	param([Parameter(ValueFromRemainingArguments=$true)] $args)
	$cmdArgs = @()
	if ($args) { $cmdArgs = $args }
	if ($cmdArgs.Count -eq 0) { & python.exe; return }
	if ($Global:AUTO_YES) {
		$yesCmd = Join-Path $PSScriptRoot 'bin\\yes.cmd'
		& $yesCmd | & python.exe @cmdArgs
	} else {
		& python.exe @cmdArgs
	}
}

Write-Output "Added $bin to PATH for this session. AUTO_YES = $Global:AUTO_YES" 
