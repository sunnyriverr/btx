$ErrorActionPreference = 'Stop'
$records = Join-Path $env:GITHUB_WORKSPACE 'pr467-records'
New-Item -ItemType Directory -Path $records -Force | Out-Null
$root = Join-Path $env:RUNNER_TEMP ('pr467-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $root | Out-Null
$image = Join-Path $root 'bounded.vhd'
$limit = 64MB
$state = [ordered]@{status='SETUP'; cap_bytes=$limit; cases=@(); cleanup=$false}
$before = @(Get-Disk | Select-Object -ExpandProperty Number)
function Save {
  $state | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $records 'pilot.json')
}
function RunCase([string]$mode, [string]$phase, [int]$index) {
  $path = Join-Path $mount "$mode-$phase-$index.bin"
  $line = & "$env:GITHUB_WORKSPACE\probe.exe" $path $mode $phase
  $code = $LASTEXITCODE
  $state.cases += [ordered]@{phase=$phase; index=$index; exit=$code; observed=($line | ConvertFrom-Json)}
  Save

}
try {
  $admin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
  if (!$admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Runner is not elevated' }
  $script = Join-Path $root 'create.txt'
  Set-Content -Encoding ascii -Path $script -Value "create vdisk file=`"$image`" maximum=64 type=expandable"
  & diskpart.exe /s $script | Set-Content (Join-Path $records 'diskpart.txt')
  if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $image)) { throw 'VHD creation failed' }
  $disk = Mount-DiskImage -ImagePath $image -PassThru | Get-Disk
  if (!$disk -or $disk.Number -in $before -or $disk.IsBoot -or $disk.IsSystem -or $disk.Size -ne $limit -or $disk.PartitionStyle -ne 'RAW') {
    throw 'New bounded VHD identity could not be proved'
  }
  $disk | Initialize-Disk -PartitionStyle MBR
  $partition = New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
  $volume = $partition | Format-Volume -FileSystem FAT -NewFileSystemLabel BTX467PILOT -AllocationUnitSize 4096 -Confirm:$false
  if ($volume.DriveLetter -eq $env:SystemDrive.TrimEnd(':') -or !$volume.DriveLetter -or $volume.Size -gt $limit) { throw 'Unexpected test volume' }
  $mount = "$($volume.DriveLetter):\"
  $state.volume = @{number=$disk.Number; letter=$volume.DriveLetter; bytes=$volume.Size; filesystem=$volume.FileSystem}
  RunCase old healthy 0
  RunCase checked healthy 0
  $fill = Join-Path $mount 'padding.bin'
  $stream = [IO.File]::Open($fill,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try {
    $chunk = [byte[]]::new(1MB)
    $written = 0
    $available = [long](Get-Volume -DriveLetter $volume.DriveLetter).SizeRemaining
    while ($written -lt $available) {
      $count = [int][Math]::Min($chunk.Length,$available-$written)
      try { $stream.Write($chunk,0,$count); $stream.Flush(); $written += $count }
      catch [IO.IOException] {
        if (($_.Exception.HResult -band 65535) -notin 39,112) { throw }
        break
      }
    }
  } finally { $stream.Dispose() }
  $state.free_bytes = (Get-Volume -DriveLetter $volume.DriveLetter).SizeRemaining
  if ($state.free_bytes -ge 4096) { throw 'Fixture still has a writable cluster' }
  foreach ($n in 1..3) {
    RunCase old full $n
    RunCase checked full $n
  }
  Remove-Item -LiteralPath $fill
  RunCase old recovered 0
  RunCase checked recovered 0
  if (@($state.cases | Where-Object exit -ne 0).Count) { throw 'One or more native controls differed from expectations' }
  $state.status = 'NATIVE_STORAGE_FIXTURE_PASS'
} catch {
  $state.error = $_.Exception.Message
  $state.line = $_.InvocationInfo.ScriptLineNumber
  throw
} finally {
  try {
    if (Test-Path -LiteralPath $image) {
      if ((Get-DiskImage -ImagePath $image).Attached) { Dismount-DiskImage -ImagePath $image }
      if ((Get-DiskImage -ImagePath $image).Attached) { throw 'Disposable image remains attached' }
    }
    Remove-Item -LiteralPath $root -Recurse -Force
    $state.cleanup = !(Test-Path -LiteralPath $root)
  } finally { Save }
}
