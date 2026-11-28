$ErrorActionPreference = 'Stop'

function Run-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command exited with $LASTEXITCODE" }
}

function Invoke-Suite {
    param([string]$Binary, [string]$Report, [string[]]$Arguments)
    $output = & $Binary @Arguments 2>&1
    $script:suiteExit = $LASTEXITCODE
    $output | Tee-Object -FilePath $Report | Out-Host
    return ($output -join "`n")
}

function Assert-SourceHash {
    param([string]$Path, [string]$Expected)
    $text = [IO.File]::ReadAllText((Resolve-Path $Path)).Replace("`r`n", "`n")
    $bytes = [Text.Encoding]::UTF8.GetBytes($text)
    $hash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    if ($hash -ne $Expected) { throw "Unexpected source hash in $Path" }
}

New-Item -Force -ItemType Directory -Path records | Out-Null
Assert-SourceHash source/src/compat/wide128.h b9fae42faea352f2d813e76b38bc528d02f3c473460b53f894b5a2566eae1bd5
Assert-SourceHash source/src/test/wide128_tests.cpp e30e7a92913839edacaa3eaae87f6f76d4ffce945011e59e4d54e87139ea9709
(Get-FileHash control/wide128-tests.patch).Hash | Out-File records/patch-hash.txt

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$install = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$install) { throw 'Visual Studio C++ toolchain not found' }
Import-Module (Join-Path $install 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $install -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64 -vcvars_ver=14.44'
$guard = @'
#if !defined(_MSC_VER) || defined(__clang__) || !defined(_M_X64) || _MSC_FULL_VER != 194435230
#error Expected native MSVC 19.44.35230 x64
#endif
'@
Set-Content -Path records/compiler.h -Value $guard
(Get-Command cl.exe).Source | Out-File records/compiler-path.txt

$boost = Join-Path $env:RUNNER_TEMP 'boost-1.87.0'
if (!(Test-Path (Join-Path $boost 'boost/test/unit_test.hpp'))) { throw 'Verified Boost headers are missing' }
$flags = @(
    '/nologo', '/std:c++20', '/EHsc', '/bigobj', '/MT', '/DBOOST_TEST_NO_LIB',
    "/I$(Resolve-Path control/include)", "/I$(Resolve-Path source/src)", "/I$boost",
    "/FI$(Resolve-Path records/compiler.h)"
)
Run-Checked cl.exe ($flags + @('/c', '/Forecords/runner.obj', 'control/runner.cpp'))

function Build-Suite {
    param([string]$Source, [string]$Name)
    Run-Checked cl.exe ($flags + @("/Forecords/$Name.obj", "/Ferecords/$Name.exe", 'records/runner.obj', $Source))
}

$source = 'source/src/test/wide128_tests.cpp'
$case = 'wide128_tests/portable_full_width_known_answers'
Build-Suite $source stock
$stock = Invoke-Suite ./records/stock.exe records/stock-list.txt @('--list_content')
if ($suiteExit -ne 0 -or $stock -notmatch 'overflow_helpers_match_wrapping_add' -or $stock -match 'portable_full_width_known_answers') { throw 'Unexpected stock suite inventory' }
Assert-SourceHash control/candidate/wide128_tests.cpp c3e7ab00191e99455b96d176fd4113435aee12ae8b334ede705763c44e90aef6
Copy-Item control/candidate/wide128_tests.cpp $source -Force
Build-Suite $source candidate
$candidate = Invoke-Suite ./records/candidate.exe records/candidate.log @("--run_test=$case", '--report_level=detailed')
if ($suiteExit -ne 0 -or $candidate -notmatch '9 assertions out of 9 passed') { throw 'Candidate did not execute all nine assertions' }
$existing = Invoke-Suite ./records/candidate.exe records/existing.log @('--run_test=wide128_tests/overflow_helpers_match_wrapping_add', '--report_level=detailed')
if ($suiteExit -ne 0 -or $existing -notmatch '20 assertions out of 20 passed') { throw 'Existing overflow checks did not pass' }

$sourceText = Get-Content $source -Raw
$expected = 'numerator % divisor == Unsigned{2}'
if ([regex]::Matches($sourceText, [regex]::Escape($expected)).Count -ne 1) { throw 'Ambiguous negative control' }
$sourceText.Replace($expected, 'numerator % divisor == Unsigned{3}') | Set-Content records/negative.cpp
Build-Suite records/negative.cpp negative
$negative = Invoke-Suite ./records/negative.exe records/negative.log @("--run_test=$case", '--report_level=detailed')
if ($suiteExit -ne 201 -or $negative -notmatch 'numerator % divisor' -or $negative -notmatch '1 assertion out of 9 failed') { throw 'Wrong expected word did not fail the intended assertion' }
Get-FileHash records/stock.exe,records/candidate.exe,records/negative.exe | Out-File records/binary-hashes.txt
Remove-Item records/*.obj,records/*.exe
'PASS: stock inventory, candidate case, existing case, deliberate wrong-answer rejection' | Tee-Object -FilePath records/verdict.txt
