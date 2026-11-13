param([string]$Candidate,[string]$Output)
$ErrorActionPreference='Stop'
$Out=Join-Path $Output 'windows-unit';[void][IO.Directory]::CreateDirectory($Out)
$RunId=[guid]::NewGuid().ToString();$Active='isolated_unit'
$code=[IO.File]::ReadAllText((Join-Path $Candidate 'guard.ps1'))
$a=$code.IndexOf('$script:LinuxRunId=');$z=$code.IndexOf('$Active=$null;')
. ([scriptblock]::Create($code.Substring($a,$z-$a)))
function Frame($q){return @{protocol='single_clock_v1';valid=$true;run_id='sampler-test';guard_run_id=$RunId
 request_seq=$q.request_seq;nonce=$q.nonce;seq=1;utc=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
 sample_seconds=.001;gpu_total=64GB;gpu_used=2GB;gpu_free=62GB;wsl_available=20GB;wsl_total=22GB;swap_used=0}}
$cases=@('normal','utc_future','utc_past','expired','cross_sampler','cross_guard','wrong_nonce','replay','invalid',
 'slow','missing_value','negative','bad_request_type','consumed','monotonic_reversed','old_response_no_refresh')
$results=[Collections.Generic.List[object]]::new()
foreach($case in $cases){
 $script:RequestSeq=0;$script:ConsumedRequestSeq=0;$script:Outstanding=$null
 $script:LinuxSeq=0;$script:LinuxRunId='sampler-test';$script:PrimarySensorFailure=$null
 $q=NewChallenge (Mono);$g=Frame $q;$expect=$null
 switch($case){
  utc_future{$g.utc+=3600}
  utc_past{$g.utc-=3600}
  expired{$q.windows_t0_ticks-=[long](3.1*[Diagnostics.Stopwatch]::Frequency);$expect='CAUSAL_SAMPLE_TIMEOUT'}
  cross_sampler{$g.run_id='wrong';$expect='LINUX_RUN_MISMATCH'}
  cross_guard{$g.guard_run_id='wrong';$expect='LINUX_GUARD_RUN_MISMATCH'}
  wrong_nonce{$g.nonce='old';$expect='LINUX_ACK_MISMATCH'}
  replay{$script:LinuxSeq=1;$expect='LINUX_RESPONSE_REPLAY'}
  invalid{$g.valid=$false;$g.error_detail='injected';$expect='LINUX_SAMPLE_INVALID'}
  slow{$g.sample_seconds=2.1;$expect='LINUX_SAMPLE_DELAY'}
  missing_value{$g.Remove('gpu_free');$expect='LINUX_VALUE_INVALID'}
  negative{$g.gpu_free=-1;$expect='LINUX_VALUE_INVALID'}
  bad_request_type{$g.request_seq='not_number';$expect='LINUX_REQUEST_SEQUENCE_INVALID'}
  consumed{$script:ConsumedRequestSeq=1;$script:Outstanding.consumed=$true;$expect='CHALLENGE_ALREADY_CONSUMED'}
  monotonic_reversed{$q.windows_t0_ticks+=[long](1*[Diagnostics.Stopwatch]::Frequency);$expect='WINDOWS_MONOTONIC_REVERSED'}
  old_response_no_refresh{
   $script:ConsumedRequestSeq=1;$script:LinuxSeq=1;$script:Outstanding.consumed=$true
   $q=NewChallenge (Mono);$g.request_seq=1;$g.seq=1
   $expect='CAUSAL_SAMPLE_TIMEOUT'
  }
 }
 [IO.File]::WriteAllText((Join-Path $Out 'linux-metrics.json'),($g|ConvertTo-Json -Compress))
 $watch=[Diagnostics.Stopwatch]::StartNew();$got=$null
 try{[void](ReadLinuxMetrics $q)}catch{$got=$_.Exception.Message}
 $pass=$got -eq $expect
 if($null -eq $expect){$pass=$pass -and $script:Outstanding.consumed -and $script:ConsumedRequestSeq -eq $q.request_seq}
 else{$pass=$pass -and $script:PrimarySensorFailure.code -eq $expect}
 $results.Add(@{case=$case;expected=$expect;observed=$got;pass=$pass;seconds=$watch.Elapsed.TotalSeconds;failure=$script:PrimarySensorFailure})
}
[IO.File]::WriteAllText((Join-Path $Output 'windows-tests.json'),($results.ToArray()|ConvertTo-Json -Depth 14))
$bad=@($results|Where-Object {-not $_.pass})
Write-Output ("WINDOWS TESTS total="+$results.Count+" failed="+$bad.Count)
if($bad.Count){throw 'Windows predicate tests failed'}
