<#
Supervise one Python runner. No experiment starts unless this script is explicitly invoked.
Use a fresh LogDirectory on E. Only the child and reader processes created here are stopped.
The hidden reader worker isolates native SMART calls so a hung read cannot hang supervision.
#>
[CmdletBinding()]
param(
    [string]$Python = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$ScriptPath,
    [string[]]$RunnerArgs = @(),
    [string]$WorkingDirectory,
    [Parameter(Mandatory=$true)][string]$LogDirectory,
    [ValidateRange(1,60)][int]$IntervalSeconds = 10,
    [ValidateRange(10,120)][int]$StartupTimeoutSeconds = 30,
    [switch]$ReaderWorker,
    [int]$DiskNumber = -1,
    [string]$ExpectedModel,
    [int]$OwnerPid = 0
)
$ErrorActionPreference = 'Stop'
$env:TEMP = 'E:\CodexResearch-xi\temp'
$env:TMP = 'E:\CodexResearch-xi\temp'
$env:PYTHONDONTWRITEBYTECODE = '1'
$readerPath = 'C:\Users\admin\Documents\Codex\2026-10-25\woxinzhuang\work\SsdTemperatureReader.ps1'
$utf8 = [Text.UTF8Encoding]::new($false)
$root = 'E:\CodexResearch-xi\'
$logPath = [IO.Path]::GetFullPath($LogDirectory)
if (-not $logPath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)) { throw 'Logs must remain under E:\CodexResearch-xi' }
$currentPath = Join-Path $logPath 'temperature_current.json'
$samplesPath = Join-Path $logPath 'temperature_samples.jsonl'
# One lock per normalized log directory, shared by this supervisor and its reader.
# Native SMART reads are outside this lock; only temperature file I/O is serialized.
$canonicalLogPath = $logPath.TrimEnd([char[]]@('\','/')).ToUpperInvariant()
$mutexHasher = [Security.Cryptography.SHA256]::Create()
try { $mutexHash = [BitConverter]::ToString($mutexHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonicalLogPath))).Replace('-','') }
finally { $mutexHasher.Dispose() }
$temperatureMutexName = 'Local\CodexResearchV447Temperature_' + $mutexHash
$temperatureMutex = [Threading.Mutex]::new($false,$temperatureMutexName)
function Invoke-TemperatureFileLock([scriptblock]$Action) {
    $acquired = $false
    try {
        try { $acquired = $temperatureMutex.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] {
            # WaitOne grants ownership on abandonment. Release it in finally, then fail closed.
            $acquired = $true
            throw 'Temperature file mutex was abandoned'
        }
        if (-not $acquired) { throw 'Temperature file mutex wait exceeded 1000 ms' }
        & $Action
    } finally {
        if ($acquired) { $temperatureMutex.ReleaseMutex() }
    }
}
function Write-Json([string]$Path, $Value) {
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 10),$utf8)
}
function Publish-Temperature($Value) {
    Invoke-TemperatureFileLock {
        [IO.File]::AppendAllText($samplesPath,(($Value | ConvertTo-Json -Depth 8 -Compress)+[Environment]::NewLine),$utf8)
        $nextPath = Join-Path $logPath 'temperature_current.next'
        Write-Json $nextPath $Value
        if ([IO.File]::Exists($currentPath)) { [IO.File]::Replace($nextPath,$currentPath,(Join-Path $logPath 'temperature_previous.json')) }
        else { [IO.File]::Move($nextPath,$currentPath) }
    }
}
function Quote-WindowsArgument([string]$Value) {
    # Windows CommandLineToArgvW/CRT quotation, including embedded quotes and final backslashes.
    $b = [Text.StringBuilder]::new()
    [void]$b.Append('"')
    $slashes = 0
    foreach ($ch in $Value.ToCharArray()) {
        if ($ch -eq '\') { $slashes++; continue }
        if ($ch -eq '"') {
            [void]$b.Append(('\' * (2*$slashes+1)))
            [void]$b.Append('"')
        } else {
            [void]$b.Append(('\' * $slashes))
            [void]$b.Append($ch)
        }
        $slashes = 0
    }
    [void]$b.Append(('\' * (2*$slashes)))
    [void]$b.Append('"')
    return $b.ToString()
}
function Stop-OwnedProcess($Process) {
    if ($null -ne $Process) {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            # Use the process object returned by Start-Process, never a process-name search.
            $Process.Kill()
            [void]$Process.WaitForExit(5000)
            $Process.Refresh()
            if (-not $Process.HasExited) { throw ('Cannot stop owned PID '+$Process.Id) }
        }
    }
}
if ($ReaderWorker) {
    if (-not [IO.Directory]::Exists($logPath) -or $DiskNumber -lt 0 -or -not $ExpectedModel) { throw 'Invalid worker configuration' }
    $sequence = 0
    try {
        . $readerPath
        $watch = [Diagnostics.Stopwatch]::StartNew()
        $due = 0.0
        while ($true) {
            if ($OwnerPid -gt 0 -and -not (Get-Process -Id $OwnerPid -ErrorAction SilentlyContinue)) { exit 3 }
            while ($watch.Elapsed.TotalSeconds -lt $due) { Start-Sleep -Milliseconds 100 }
            $reading = [SsdTemperatureNative]::Read($DiskNumber)
            if ($reading.Model -ne $ExpectedModel -or $reading.Model -notlike '*GM6*') { throw 'SMART identity mismatch' }
            $composite = @($reading.Sensors | Where-Object Index -eq 0)
            if ($composite.Count -ne 1) { throw 'Missing or ambiguous SMART composite sensor' }
            $maximum = ($reading.Sensors.Celsius | Measure-Object -Maximum).Maximum
            $status = 'OK'
            $reason = $null
            if ([int]$composite[0].Celsius -ge 60 -or $maximum -ge 60) { $status='FAIL'; $reason='STOP_AT_60_C' }
            $row = [ordered]@{
                Status=$status; Sequence=$sequence; TimeUTC=[DateTimeOffset]::UtcNow.ToString('o')
                DiskNumber=$DiskNumber; Model=$reading.Model; CompositeC=[int]$composite[0].Celsius
                MaximumReportedSensorC=$maximum; Sensors=$reading.Sensors; Failure=$reason
            }
            Publish-Temperature $row
            if ($status -ne 'OK') { exit 2 }
            $sequence++
            $due += $IntervalSeconds
            # Avoid a burst after delayed native reads; the parent enforces freshness separately.
            if ($due -lt $watch.Elapsed.TotalSeconds) { $due=$watch.Elapsed.TotalSeconds+$IntervalSeconds }
        }
    } catch {
        $row = [ordered]@{Status='FAIL';Sequence=$sequence;TimeUTC=[DateTimeOffset]::UtcNow.ToString('o');DiskNumber=$DiskNumber;Model=$ExpectedModel;Failure=$_.Exception.Message}
        try { Publish-Temperature $row } catch { }
        [Console]::Error.WriteLine($_.Exception.Message)
        exit 1
    } finally {
        $temperatureMutex.Dispose()
    }
}
# Supervisor mode. Validate paths and capture mapping before starting any workload.
if ([IO.Directory]::Exists($logPath) -or [IO.File]::Exists($logPath)) { throw 'Fresh LogDirectory required; preserve earlier evidence' }
[void][IO.Directory]::CreateDirectory($logPath)
$child = $null
$worker = $null
$summary = [ordered]@{
    Status='FAIL_CLOSED'; StartedUTC=[DateTimeOffset]::UtcNow.ToString('o'); EndedUTC=$null
    ChildPid=$null; ReaderPid=$null; ChildExitCode=$null; ChildStarted=$false
    ChildTerminatedBySupervisor=$false; Failure=$null; IntervalSeconds=$IntervalSeconds
    StopAtC=60; ReadTimeoutSeconds=([math]::Max(20,2*$IntervalSeconds+5))
    TemperatureFileMutexName=$temperatureMutexName; TemperatureFileMutexWaitMilliseconds=1000
    AvailableBytesAtStart=[IO.DriveInfo]::new('E').AvailableFreeSpace; AvailableBytesAtEnd=$null
    LastTemperature=$null; Mapping=$null; ScriptPath=$ScriptPath; RunnerArgs=$RunnerArgs
}
$lastSequence = -1
$freshWatch = [Diagnostics.Stopwatch]::StartNew()
function Get-CheckedCurrent {
    $row = Invoke-TemperatureFileLock {
        if (-not [IO.File]::Exists($currentPath)) { return $null }
        [IO.File]::ReadAllText($currentPath) | ConvertFrom-Json
    }
    if ($null -eq $row) { return $null }
    if ($row.Status -ne 'OK') { throw ('Temperature monitoring failed: '+$row.Failure) }
    if ([int]$row.DiskNumber -ne [int]$disk.Number -or $row.Model -ne $disk.FriendlyName) { throw 'Monitor device identity mismatch' }
    if ($null -eq $row.CompositeC -or $null -eq $row.MaximumReportedSensorC -or $null -eq $row.Sequence) { throw 'Incomplete temperature sample' }
    if ([int]$row.CompositeC -ge 60 -or [int]$row.MaximumReportedSensorC -ge 60) { throw 'STOP_AT_60_C' }
    if ([int]$row.Sequence -ne $script:lastSequence) {
        if ([int]$row.Sequence -lt $script:lastSequence) { throw 'Temperature sequence regressed' }
        $script:lastSequence = [int]$row.Sequence
        $script:freshWatch.Restart()
    }
    return $row
}
try {
    if (-not [IO.File]::Exists($Python)) { throw 'Python executable not found' }
    if (-not $ScriptPath -or -not $WorkingDirectory) { throw 'ScriptPath and WorkingDirectory are required' }
    $scriptFull = [IO.Path]::GetFullPath($ScriptPath)
    $workFull = [IO.Path]::GetFullPath($WorkingDirectory)
    if (-not $scriptFull.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or -not [IO.File]::Exists($scriptFull)) { throw 'Runner must be an existing E research file' }
    if (-not $workFull.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or -not [IO.Directory]::Exists($workFull)) { throw 'Working directory must be on E research storage' }
    if ($summary.AvailableBytesAtStart -lt 10GB) { throw 'Less than 10 GiB reserve on E' }
    $partition = Get-Partition -DriveLetter E
    $disk = $partition | Get-Disk
    if (@($disk).Count -ne 1 -or $disk.FriendlyName -notlike '*Predator*GM6*') { throw 'Unexpected E physical-disk mapping' }
    if ([string]$disk.HealthStatus -ne 'Healthy') { throw 'E disk health is not Healthy' }
    $summary.Mapping = [ordered]@{Drive='E';DiskNumber=[int]$disk.Number;PhysicalDevice=('\\.\PhysicalDrive'+$disk.Number);Model=$disk.FriendlyName;SerialNumber=$disk.SerialNumber;BusType=[string]$disk.BusType;HealthStatus=[string]$disk.HealthStatus;PartitionNumber=[int]$partition.PartitionNumber}
    $summary.ReaderSHA256 = (Get-FileHash -LiteralPath $readerPath -Algorithm SHA256).Hash
    $summary.MonitorSHA256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
    Write-Json (Join-Path $logPath 'PROTOCOL.json') $summary
    $shellPath = Join-Path $PSHOME 'pwsh.exe'
    if (-not [IO.File]::Exists($shellPath)) { $shellPath = Join-Path $PSHOME 'powershell.exe' }
    $workerArgs = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-ReaderWorker','-LogDirectory',$logPath,'-IntervalSeconds',[string]$IntervalSeconds,'-DiskNumber',[string]$disk.Number,'-ExpectedModel',$disk.FriendlyName,'-OwnerPid',[string]$PID)
    $workerCommand = ($workerArgs | ForEach-Object { Quote-WindowsArgument ([string]$_) }) -join ' '
    $worker = Start-Process -FilePath $shellPath -ArgumentList $workerCommand -WorkingDirectory $workFull -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logPath 'reader_stdout.log') -RedirectStandardError (Join-Path $logPath 'reader_stderr.log')
    $summary.ReaderPid = $worker.Id
    $startup = [Diagnostics.Stopwatch]::StartNew()
    do {
        $worker.Refresh()
        $sample = Get-CheckedCurrent
        if ($worker.HasExited) { throw 'Reader exited before child launch' }
        if ($null -ne $sample) { break }
        if ($startup.Elapsed.TotalSeconds -ge $StartupTimeoutSeconds) { throw 'Initial temperature reading timed out' }
        Start-Sleep -Milliseconds 200
    } while ($true)
    $summary.LastTemperature = $sample
    $childArguments = @('-B','-X','utf8',$scriptFull) + $RunnerArgs
    $childCommand = ($childArguments | ForEach-Object { Quote-WindowsArgument ([string]$_) }) -join ' '
    $child = Start-Process -FilePath $Python -ArgumentList $childCommand -WorkingDirectory $workFull -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logPath 'child_stdout.log') -RedirectStandardError (Join-Path $logPath 'child_stderr.log')
    $summary.ChildPid=$child.Id; $summary.ChildStarted=$true
    Write-Json (Join-Path $logPath 'STARTED.json') $summary
    while ($true) {
        $worker.Refresh()
        $sample = Get-CheckedCurrent
        if ($worker.HasExited) { throw 'Reader process exited while supervising child' }
        if ($null -eq $sample -or $freshWatch.Elapsed.TotalSeconds -gt $summary.ReadTimeoutSeconds) { throw 'Temperature sample missing or stale; native reader may have stalled' }
        $summary.LastTemperature=$sample
        $child.Refresh()
        if ($child.HasExited) { break }
        Start-Sleep -Milliseconds 200
    }
    $child.WaitForExit()
    $summary.ChildExitCode=$child.ExitCode
    if ($child.ExitCode -ne 0) { throw ('Child exited with code '+$child.ExitCode) }
    $summary.Status='PASS'
} catch {
    $summary.Failure=$_.Exception.Message
    if ($null -ne $child) {
        $child.Refresh()
        if (-not $child.HasExited) {
            $summary.ChildTerminatedBySupervisor=$true
            try { Stop-OwnedProcess $child } catch { $summary.Failure += '; '+$_.Exception.Message }
        }
    }
    Write-Json (Join-Path $logPath 'FAILURE.json') $summary
} finally {
    try { Stop-OwnedProcess $worker } catch { $summary.Status='FAIL_CLOSED'; $summary.Failure += '; '+$_.Exception.Message }
    if ($null -ne $child) { $child.Refresh(); if ($child.HasExited) { $summary.ChildExitCode=$child.ExitCode } }
    $temperatureMutex.Dispose()
    $summary.EndedUTC=[DateTimeOffset]::UtcNow.ToString('o')
    $summary.AvailableBytesAtEnd=[IO.DriveInfo]::new('E').AvailableFreeSpace
    Write-Json (Join-Path $logPath 'PROCESS_COMPLETE.json') $summary
    $summary | ConvertTo-Json -Depth 10
}
if ($summary.Status -ne 'PASS') { exit 1 }
