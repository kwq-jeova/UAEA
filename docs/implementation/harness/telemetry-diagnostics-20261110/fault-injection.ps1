param([string]$LaunchRoot,[string]$Output)
$ErrorActionPreference='Stop'
$Out=Join-Path $Output 'injection';[void][IO.Directory]::CreateDirectory($Out)
$Active='isolated_injection';$script:CurrentWindowsSensor=@{utc=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0}
$raw=[IO.File]::ReadAllText((Join-Path $LaunchRoot 'guard.ps1'))
$start=$raw.IndexOf('$script:LinuxRunId=')
$end=$raw.IndexOf('$Active=$null;')
. ([scriptblock]::Create($raw.Substring($start,$end-$start)))
function Frame {return @{valid=$true;run_id='test-run';seq=1;utc=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0;sample_seconds=.001;gpu_total=64GB;gpu_used=2GB;gpu_free=62GB;wsl_available=20GB;wsl_total=22GB;swap_used=0}}
$results=[Collections.Generic.List[object]]::new()
foreach($name in @('valid','old','future','delay','invalid','wrong_run','negative','missing','bad_type','sequence_reverse','sequence_stale','bad_json')){
 $script:LinuxRunId='test-run';$script:LinuxSeq=-1;$script:LinuxSeen=[Diagnostics.Stopwatch]::StartNew();$script:LastGoodLinux=$null;$script:PrimarySensorFailure=$null
 $g=Frame
 [IO.File]::WriteAllText((Join-Path $Out 'linux-metrics.json'),($g|ConvertTo-Json))
 [void](ReadLinuxMetrics)
 $g=Frame;$g.seq=2;$expected=$null
 switch($name){
  old{$g.utc-=4;$expected='LINUX_SAMPLE_OLD'}
  future{$g.utc+=2;$expected='LINUX_CLOCK_FUTURE'}
  delay{$g.sample_seconds=3.1;$expected='LINUX_SAMPLE_DELAY'}
  invalid{$g.valid=$false;$g.error='NvmlError';$expected='LINUX_SAMPLE_INVALID'}
  wrong_run{$g.run_id='wrong';$expected='LINUX_RUN_MISMATCH'}
  negative{$g.gpu_free=-1;$expected='LINUX_VALUE_INVALID'}
  missing{$g.Remove('gpu_used');$expected='LINUX_VALUE_INVALID'}
  bad_type{$g.gpu_used='wrong';$expected='LINUX_VALUE_INVALID'}
  sequence_reverse{$g.seq=0;$expected='LINUX_SEQUENCE_REVERSED'}
  sequence_stale{$g.seq=1;Start-Sleep -Milliseconds 3100;$g.utc=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0;$expected='LINUX_SEQUENCE_STALE'}
  bad_json{$expected='LINUX_SAMPLE_UNREADABLE'}
 }
 [IO.File]::WriteAllText((Join-Path $Out 'linux-metrics.json'),$(if($name -eq 'bad_json'){'not json'}else{$g|ConvertTo-Json}))
 $observed=$null
 try{[void](ReadLinuxMetrics)}catch{$observed=$_.Exception.Message}
 $match=$observed -eq $expected
 if($expected){$match=$match -and $script:PrimarySensorFailure.code -eq $expected -and $null -ne $script:PrimarySensorFailure.last_accepted_sample -and $script:PrimarySensorFailure.action -eq 'FAIL_CLOSED'}
 $results.Add(@{case=$name;expected=$expected;observed=$observed;pass=$match;failure=$script:PrimarySensorFailure})
}
function Resource {return [pscustomobject]@{sample_seconds=.01;windows=@{commit_limit=100GB;commit_used=40GB;physical_available=30GB;gpu_dedicated_usage=2GB};wsl_gpu=@{gpu_total=64GB;gpu_used=2GB;wsl_available=20GB;swap_used=0}}}
foreach($name in @('normal','gpu','dedicated','commit','physical','wsl','swap','capacity','sensor')){
 $x=Resource;$expected=$null
 switch($name){
  gpu{$x.wsl_gpu.gpu_used=48GB;$expected='GPU_48GIB'}
  dedicated{$x.windows.gpu_dedicated_usage=48GB;$expected='WDDM_DEDICATED_48GIB'}
  commit{$x.windows.commit_used=80GB;$expected='WINDOWS_COMMIT'}
  physical{$x.windows.physical_available=5GB;$expected='WINDOWS_PHYSICAL'}
  wsl{$x.wsl_gpu.wsl_available=3GB;$expected='WSL_MEMORY'}
  swap{$x.wsl_gpu.swap_used=257MB;$expected='WSL_SWAP'}
  capacity{$x.wsl_gpu.gpu_total=63GB;$expected='GPU_CAPACITY_CHANGED'}
  sensor{$x.sample_seconds=3.1;$expected='SENSOR_DELAY'}
 }
 $observed=Reason $x
 $results.Add(@{case='resource_'+$name;expected=$expected;observed=$observed;pass=($expected -eq $observed)})
}
[IO.File]::WriteAllText((Join-Path $Output 'fault-injection.json'),($results.ToArray()|ConvertTo-Json -Depth 14))
$bad=@($results|Where-Object {-not $_.pass})
Write-Output ("INJECTION total="+$results.Count+" failed="+$bad.Count)
if($bad.Count){throw 'Fault injection failed'}
