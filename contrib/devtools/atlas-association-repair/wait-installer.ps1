param([Parameter(Mandatory=$true)][string]$Executable,
      [Parameter(Mandatory=$true)][string]$Arguments,
      [Parameter(Mandatory=$true)][string]$Observation)
$ErrorActionPreference = 'Stop'
# -Wait includes Windows descendants, including NSIS's self-copied uninstaller.
$p = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $env:RUNNER_TEMP -PassThru -Wait
@{ launcher_pid = $p.Id; launcher_exit = $p.ExitCode; wait_mode = 'Start-Process -Wait process tree' } | ConvertTo-Json | Set-Content -LiteralPath $Observation -Encoding utf8
exit $p.ExitCode
