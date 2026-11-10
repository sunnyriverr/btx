$ErrorActionPreference = 'Stop'
$records = Join-Path $env:GITHUB_WORKSPACE 'pr470-records'
New-Item -ItemType Directory -Path $records -Force | Out-Null
$root = Join-Path $env:RUNNER_TEMP ('pr470-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $root | Out-Null
$image = Join-Path $root 'bounded.vhd'
$limit = 64MB
$state = [ordered]@{status='SETUP'; cap_bytes=$limit; cases=@(); cleanup=$false}
$before = @(Get-Disk | Select-Object -ExpandProperty Number)
function Save {
  $state | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $records 'volume.json')
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
  $volume = $partition | Format-Volume -FileSystem FAT -NewFileSystemLabel BTX470TEST -AllocationUnitSize 4096 -Confirm:$false
  if ($volume.DriveLetter -eq $env:SystemDrive.TrimEnd(':') -or !$volume.DriveLetter -or $volume.Size -gt $limit) { throw 'Unexpected test volume' }
  $mount = "$($volume.DriveLetter):\"
  $state.volume = @{number=$disk.Number; letter=$volume.DriveLetter; bytes=$volume.Size; filesystem=$volume.FileSystem}
  $baseline = Join-Path $env:RUNNER_TEMP 'pr470-baseline/btxd.exe'
  $candidate = 'D:\btx-native-035\project-build\bin\btxd.exe'
  & python "$env:GITHUB_WORKSPACE\wallet_export.py" $mount $baseline $candidate
  if ($LASTEXITCODE -ne 0) { throw "Wallet comparison failed with exit $LASTEXITCODE" }
  $state.status = 'NATIVE_LABEL_EXPORT_MATRIX_PASS' 
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
