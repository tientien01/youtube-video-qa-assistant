$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
}

if ($null -eq $pythonCommand) {
    throw "Python was not found. Install Python 3.12 as documented in docs/07-operations/local-development.md."
}

& $pythonCommand.Source "scripts/verify.py"
exit $LASTEXITCODE
