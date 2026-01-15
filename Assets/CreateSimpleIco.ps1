# Simple ICO creator using existing PNG files
Add-Type -AssemblyName System.Drawing

$assetsPath = $PSScriptRoot
$icoPath = Join-Path $assetsPath "JobTracker.ico"

# Find existing PNG files to use
$sizes = @(16, 24, 32, 48, 256)
$pngFiles = @()

foreach ($size in $sizes) {
    $candidates = @(
        "Square44x44Logo.targetsize-$size.png",
        "Square44x44Logo.scale-200.png",
        "Square150x150Logo.scale-100.png"
    )
    
    foreach ($candidate in $candidates) {
        $path = Join-Path $assetsPath $candidate
        if (Test-Path $path) {
            $pngFiles += @{Size=$size; Path=$path}
            break
        }
    }
}

# If we don't have enough, use the 256 size one
$largePng = Join-Path $assetsPath "Square44x44Logo.targetsize-256.png"
if (-not (Test-Path $largePng)) {
    $largePng = Join-Path $assetsPath "Square150x150Logo.scale-200.png"
}

if (-not (Test-Path $largePng)) {
    Write-Host "ERROR: No suitable PNG files found"
    exit 1
}

# Create ICO using the PNG
$images = @()
$imageData = @()

foreach ($size in @(16, 32, 48, 256)) {
    $img = [System.Drawing.Image]::FromFile($largePng)
    $resized = New-Object System.Drawing.Bitmap($size, $size)
    $g = [System.Drawing.Graphics]::FromImage($resized)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($img, 0, 0, $size, $size)
    $g.Dispose()
    $img.Dispose()
    
    $ms = New-Object System.IO.MemoryStream
    $resized.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $imageData += ,($ms.ToArray())
    $images += $resized
    $ms.Dispose()
}

# Write ICO file
$fs = [System.IO.File]::Create($icoPath)
$bw = New-Object System.IO.BinaryWriter($fs)

# ICO header
$bw.Write([Int16]0)           # Reserved
$bw.Write([Int16]1)           # Type: ICO
$bw.Write([Int16]$images.Count) # Number of images

$offset = 6 + (16 * $images.Count)

# Directory entries
for ($i = 0; $i -lt $images.Count; $i++) {
    $img = $images[$i]
    $data = $imageData[$i]
    
    $width = if ($img.Width -ge 256) { 0 } else { $img.Width }
    $height = if ($img.Height -ge 256) { 0 } else { $img.Height }
    
    $bw.Write([Byte]$width)
    $bw.Write([Byte]$height)
    $bw.Write([Byte]0)          # Color palette
    $bw.Write([Byte]0)          # Reserved
    $bw.Write([Int16]1)         # Color planes
    $bw.Write([Int16]32)        # Bits per pixel
    $bw.Write([Int32]$data.Length)
    $bw.Write([Int32]$offset)
    
    $offset += $data.Length
}

# Image data
foreach ($data in $imageData) {
    $bw.Write($data)
}

$bw.Close()
$fs.Close()

# Cleanup
foreach ($img in $images) {
    $img.Dispose()
}

Write-Host "Created: $icoPath"
