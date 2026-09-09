param(
    [Parameter(Mandatory = $true)][string]$VideoPath,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [double]$IntervalSeconds = 1.0,
    [double]$SceneThreshold = 0.08,
    [string]$FfmpegPath = "",
    [string]$FfprobePath = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $VideoPath -PathType Leaf)) { throw "Video not found: $VideoPath" }
if ($IntervalSeconds -le 0) { throw "IntervalSeconds must be positive" }

function Resolve-MediaTool([string]$ExplicitPath, [string]$Name) {
    if ($ExplicitPath -and (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) { return $ExplicitPath }
    $cmd = Get-Command "$Name.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $root = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path -LiteralPath $root) {
        $found = Get-ChildItem -LiteralPath $root -Filter "$Name.exe" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    throw "$Name was not found. Pass -${Name}Path explicitly."
}

$ffmpeg = Resolve-MediaTool $FfmpegPath "ffmpeg"
$ffprobe = Resolve-MediaTool $FfprobePath "ffprobe"
$fixedDir = Join-Path $OutputDir "fixed"
$sceneDir = Join-Path $OutputDir "scene-change"
New-Item -ItemType Directory -Force -Path $fixedDir, $sceneDir | Out-Null

& $ffprobe -v error -show_streams -show_format -of json $VideoPath | Set-Content -LiteralPath (Join-Path $OutputDir "media-probe.json") -Encoding utf8
$fpsExpr = "fps=1/$IntervalSeconds,scale=540:-2"
& $ffmpeg -hide_banner -loglevel error -i $VideoPath -vf $fpsExpr -q:v 3 -y (Join-Path $fixedDir "fixed-%05d.jpg")
if ($LASTEXITCODE -ne 0) { throw "Fixed-interval frame extraction failed with exit code $LASTEXITCODE" }
$sceneExpr = "select='gt(scene,$SceneThreshold)',scale=540:-2"
& $ffmpeg -hide_banner -loglevel error -i $VideoPath -vf $sceneExpr -fps_mode vfr -y (Join-Path $sceneDir "scene-%05d.png")
if ($LASTEXITCODE -ne 0) { throw "Scene-change frame extraction failed with exit code $LASTEXITCODE" }

$fixed = Get-ChildItem -LiteralPath $fixedDir -Filter "fixed-*.jpg" | Sort-Object Name
$index = for ($i = 0; $i -lt $fixed.Count; $i++) {
    [pscustomobject]@{ frame = $fixed[$i].Name; approx_seconds = [math]::Round($i * $IntervalSeconds, 3) }
}
$index | Export-Csv -LiteralPath (Join-Path $OutputDir "fixed-frames.csv") -NoTypeInformation -Encoding utf8

[pscustomobject]@{
    video = (Resolve-Path -LiteralPath $VideoPath).Path
    fixed_frames = $fixed.Count
    scene_change_frames = (Get-ChildItem -LiteralPath $sceneDir -Filter "scene-*.png").Count
    interval_seconds = $IntervalSeconds
    scene_threshold = $SceneThreshold
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputDir "review-summary.json") -Encoding utf8

Get-Content -LiteralPath (Join-Path $OutputDir "review-summary.json")
