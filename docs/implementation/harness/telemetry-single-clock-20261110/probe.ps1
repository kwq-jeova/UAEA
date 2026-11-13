param([string]$LaunchRoot,[int]$Seconds=10)
$ErrorActionPreference='Stop'
$code=[IO.File]::ReadAllText((Join-Path $LaunchRoot 'guard.ps1'))
$a=$code.IndexOf('$ErrorActionPreference=');$z=$code.IndexOf('$Active=$null;')
$Check=$false;$Smoke=$true;$Experiment=$false
. ([scriptblock]::Create($code.Substring($a,$z-$a)))
$Active='isolated_no_model';$MetricsStarted=$false
try{
 $mm=Linux 'metrics_start';$MetricsStarted=$true;$script:LinuxRunId=$mm.run_id
 $sw=[Diagnostics.Stopwatch]::StartNew();$n=0
 while($sw.Elapsed.TotalSeconds -lt $Seconds){
  $sample=Sensor 'no_model_causal';$why=Reason $sample
  if($why){throw "Real resource preflight stop: $why"}
  $n++;Start-Sleep -Milliseconds 1000
 }
 Save 'probe-result.json' @{pass=$true;samples=$n;seconds=$sw.Elapsed.TotalSeconds;model_loaded=$false;requested_seconds=$Seconds}
 Write-Output ("PROBE PASS samples="+$n+" seconds="+$sw.Elapsed.TotalSeconds)
}catch{Save 'monitor-exception.json' @{message=$_.Exception.Message;active=$Active;primary_sensor_failure=$script:PrimarySensorFailure};throw}
finally{
 if($MetricsStarted){try{Save 'metrics-cleanup.json' (Linux 'metrics_stop')}catch{Save 'cleanup-error.json' @{message=$_.Exception.Message}}}
 $Counters.Dispose();$Heart.Dispose();$Log.Dispose()
}
