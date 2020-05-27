# This is probably terrible coding, but I genuinely don't know ANY PowerShell.

# Silence errors
$ErrorActionPreference="silentlycontinue"

# cd to the poptpy directory
Set-Location (Join-Path -Path (Split-Path -Path $PSScriptRoot) -ChildPath poptpy)

# Find Python executable
Write-Host "Locating Python 3 executable... " -NoNewLine
$pyex=Get-Command python3 | Select-Object -ExpandProperty Definition
If (-Not $pyex) {
    $pyex=Get-Command python | Select-Object -ExpandProperty Definition
}
If ($pyex) {
    Write-Host "$pyex"
}
Else {
    Write-Host "not found"
    Write-Host "`nError: Python 3 executable was not found."
    exit 1
}

# Check that Python version is >=3
Write-Host "Checking Python version... " -NoNewLine
$pyv=Invoke-Expression "$pyex --version 2>&1" | Out-String
$pyv=$pyv.trim()
Write-Host "${pyv}"
If ($pyv -NotLike 'Python 3*') {
    Write-Host "`nA Python executable was found at $pyex, but it was not Python 3."
    Write-Host "Please install Python 3 and make sure that it is in `$PATH."
    exit 1
}

# Set path to Python executable
Write-Host "Setting Python path in TopSpin scripts... " -NoNewLine
(Get-Content poptpy.py) -replace "^p_python3 = .*$", "p_python3 = r`"$pyex`"" | Set-Content poptpy.py
Write-Host "done"

# Find TopSpin installation directory
Write-Host "Locating TopSpin installation directory... " -NoNewLine
$tsdirs=Get-ChildItem -Path "\Bruker\topspin*\exp\stan" -Include "nmr" -Recurse -Directory | ForEach-Object {$_.FullName} 
If ($tsdirs.Count -gt 1) {
    Write-Host "$($tsdirs.Count) found`n"
    $x=1
    ForEach ($i IN $tsdirs) {
        Write-Host "${x}:  ${i}"
        $x = $x + 1
    }
    Write-Host ""
    $chosen=0
    While ($chosen -le 0 -Or $chosen -gt $tsdirs.Count) {
        $chosen=Read-Host -Prompt "Please enter number corresponding to desired TopSpin directory (q to quit)"
        If ($chosen -eq "q") {
            exit 1
        }
        $chosen=[int]$chosen
    }
    $tsdir=$tsdirs[$chosen - 1]
    Write-Host "chose $tsdir"
}
ElseIf ($tsdirs.Count -eq 1) {
    $tsdir=$tsdirs
    Write-Host "$tsdir"
}
Else {
    Write-Host "not found"
    Write-Host "`nError: TopSpin installation directory was not found."
    exit 1
}

# Install the files
Write-Host "Copying scripts to TopSpin directory... " -NoNewLine
$tspy="${tsdir}\py\user"
Copy-Item poptpy.py -Destination $tspy > $null
Copy-Item -Path "poptpy_backend" -Destination ${tspy} -Recurse > $null
Write-Host "done"

Write-Host "`nInstallation to TopSpin directory successful."
