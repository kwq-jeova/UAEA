param([string]$Output)
$ErrorActionPreference='Stop'
$results=[Collections.Generic.List[object]]::new()
$expected=@{query_error='LINUX_SAMPLE_INVALID';slow_query='LINUX_SAMPLE_INVALID';lost_ack='CAUSAL_SAMPLE_TIMEOUT';wrong_ack='LINUX_ACK_MISMATCH';cross_run='LINUX_GUARD_RUN_MISMATCH';replay='LINUX_RESPONSE_REPLAY';freeze='CAUSAL_SAMPLE_TIMEOUT'}
foreach($mode in @('query_error','slow_query','lost_ack','wrong_ack','cross_run','replay','freeze')){
 $root=Join-Path $Output ('fault-'+$mode);$lines=[Collections.Generic.List[string]]::new();$caught=$null
 try{
  & ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $root 'guard.ps1')))) -LaunchRoot $root -Smoke |ForEach-Object {$lines.Add([string]$_)}
 }catch{$caught=$_.Exception.Message}
 $log=$lines -join [Environment]::NewLine
 [IO.File]::WriteAllText((Join-Path $Output ($mode+'.log')),$log+[Environment]::NewLine+$caught)
 $match=[regex]::Match($log,'Logs:\s*(/home/[^\r\n]+)')
 if(-not $match.Success){throw "Missing owned record for $mode"}
 $linux=$match.Groups[1].Value.Trim();$record='\\wsl.localhost\Ubuntu-24.04'+$linux.Replace('/','\')
 $exception=[IO.File]::ReadAllText((Join-Path $record 'monitor-exception.json'))|ConvertFrom-Json
 $state=[IO.File]::ReadAllText((Join-Path $record 'guard_smoke_limit/state.json'))|ConvertFrom-Json
 $cleanup=[IO.File]::ReadAllText((Join-Path $record 'metrics-cleanup.json'))|ConvertFrom-Json
 $ok=$exception.message -eq $expected[$mode] -and $state.remaining.Count -eq 0 -and $cleanup.remaining.Count -eq 0 -and -not [IO.File]::Exists((Join-Path $record 'model-attempt.json'))
 $results.Add(@{mode=$mode;record=$linux;expected=$expected[$mode];actual=$exception.message;pass=$ok;state=$state;sampler_cleanup=$cleanup;primary=$exception.primary_sensor_failure})
 [IO.File]::WriteAllText((Join-Path $Output 'process-faults.json'),($results.ToArray()|ConvertTo-Json -Depth 18))
 Write-Output ("FAULT "+$mode+" pass="+$ok+" reason="+$exception.message)
 if(-not $ok){throw "Safety validation failed: $mode"}
}
