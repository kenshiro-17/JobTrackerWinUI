# Icon Generator for Job Tracker
# This script generates all required icon sizes from the SVG using .NET System.Drawing

Add-Type -AssemblyName System.Drawing

$assetsPath = $PSScriptRoot
$svgPath = Join-Path $assetsPath "AppIcon.svg"

# Icon design - programmatically drawn since we can't easily convert SVG
function Create-Icon {
    param (
        [int]$Size,
        [string]$OutputPath
    )
    
    $bitmap = New-Object System.Drawing.Bitmap($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    
    # Enable anti-aliasing
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    
    # Scale factor
    $scale = $Size / 512.0
    
    # Colors
    $pastelBlue = [System.Drawing.Color]::FromArgb(255, 168, 213, 229)
    $pastelGreen = [System.Drawing.Color]::FromArgb(255, 181, 232, 195)
    $darkColor = [System.Drawing.Color]::FromArgb(255, 26, 26, 46)
    $white = [System.Drawing.Color]::White
    
    # Background gradient (approximate with solid color blend)
    $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        (New-Object System.Drawing.Point(0, 0)),
        (New-Object System.Drawing.Point($Size, $Size)),
        $pastelBlue,
        $pastelGreen
    )
    
    # Draw rounded background
    $margin = [int](16 * $scale)
    $bgRect = New-Object System.Drawing.Rectangle($margin, $margin, ($Size - $margin * 2), ($Size - $margin * 2))
    $bgPath = New-Object System.Drawing.Drawing2D.GraphicsPath
    $radius = [int](48 * $scale)
    $bgPath.AddArc($bgRect.X, $bgRect.Y, $radius * 2, $radius * 2, 180, 90)
    $bgPath.AddArc($bgRect.Right - $radius * 2, $bgRect.Y, $radius * 2, $radius * 2, 270, 90)
    $bgPath.AddArc($bgRect.Right - $radius * 2, $bgRect.Bottom - $radius * 2, $radius * 2, $radius * 2, 0, 90)
    $bgPath.AddArc($bgRect.X, $bgRect.Bottom - $radius * 2, $radius * 2, $radius * 2, 90, 90)
    $bgPath.CloseFigure()
    $graphics.FillPath($bgBrush, $bgPath)
    
    # Briefcase body
    $briefcaseBrush = New-Object System.Drawing.SolidBrush($darkColor)
    $bx = [int](100 * $scale)
    $by = [int](180 * $scale)
    $bw = [int](312 * $scale)
    $bh = [int](200 * $scale)
    $br = [int](24 * $scale)
    
    $briefcasePath = New-Object System.Drawing.Drawing2D.GraphicsPath
    $briefcaseRect = New-Object System.Drawing.Rectangle($bx, $by, $bw, $bh)
    $briefcasePath.AddArc($briefcaseRect.X, $briefcaseRect.Y, $br * 2, $br * 2, 180, 90)
    $briefcasePath.AddArc($briefcaseRect.Right - $br * 2, $briefcaseRect.Y, $br * 2, $br * 2, 270, 90)
    $briefcasePath.AddArc($briefcaseRect.Right - $br * 2, $briefcaseRect.Bottom - $br * 2, $br * 2, $br * 2, 0, 90)
    $briefcasePath.AddArc($briefcaseRect.X, $briefcaseRect.Bottom - $br * 2, $br * 2, $br * 2, 90, 90)
    $briefcasePath.CloseFigure()
    $graphics.FillPath($briefcaseBrush, $briefcasePath)
    
    # Briefcase handle
    $handlePen = New-Object System.Drawing.Pen($darkColor, [int](28 * $scale))
    $handlePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $handlePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    
    $handlePath = New-Object System.Drawing.Drawing2D.GraphicsPath
    $hx1 = [int](180 * $scale)
    $hx2 = [int](332 * $scale)
    $hy1 = [int](180 * $scale)
    $hy2 = [int](140 * $scale)
    $hy3 = [int](110 * $scale)
    
    $handlePath.AddLine($hx1, $hy1, $hx1, $hy2)
    $handlePath.AddArc($hx1, $hy3, [int](30 * $scale), [int](30 * $scale), 180, 90)
    $handlePath.AddLine([int](210 * $scale), $hy3, [int](302 * $scale), $hy3)
    $handlePath.AddArc([int](302 * $scale), $hy3, [int](30 * $scale), [int](30 * $scale), 270, 90)
    $handlePath.AddLine($hx2, $hy2, $hx2, $hy1)
    $graphics.DrawPath($handlePen, $handlePath)
    
    # Briefcase clasp
    $claspBrush = New-Object System.Drawing.SolidBrush($pastelBlue)
    $cx = [int](230 * $scale)
    $cy = [int](250 * $scale)
    $cw = [int](52 * $scale)
    $ch = [int](60 * $scale)
    $cr = [int](8 * $scale)
    
    $claspPath = New-Object System.Drawing.Drawing2D.GraphicsPath
    $claspRect = New-Object System.Drawing.Rectangle($cx, $cy, $cw, $ch)
    $claspPath.AddArc($claspRect.X, $claspRect.Y, $cr * 2, $cr * 2, 180, 90)
    $claspPath.AddArc($claspRect.Right - $cr * 2, $claspRect.Y, $cr * 2, $cr * 2, 270, 90)
    $claspPath.AddArc($claspRect.Right - $cr * 2, $claspRect.Bottom - $cr * 2, $cr * 2, $cr * 2, 0, 90)
    $claspPath.AddArc($claspRect.X, $claspRect.Bottom - $cr * 2, $cr * 2, $cr * 2, 90, 90)
    $claspPath.CloseFigure()
    $graphics.FillPath($claspBrush, $claspPath)
    
    # Checkmark circle
    $checkCircleBrush = New-Object System.Drawing.SolidBrush($pastelGreen)
    $checkCirclePen = New-Object System.Drawing.Pen($white, [int](8 * $scale))
    $ccx = [int](390 * $scale)
    $ccy = [int](140 * $scale)
    $ccr = [int](55 * $scale)
    $graphics.FillEllipse($checkCircleBrush, $ccx - $ccr, $ccy - $ccr, $ccr * 2, $ccr * 2)
    $graphics.DrawEllipse($checkCirclePen, $ccx - $ccr, $ccy - $ccr, $ccr * 2, $ccr * 2)
    
    # Checkmark
    $checkPen = New-Object System.Drawing.Pen($darkColor, [int](14 * $scale))
    $checkPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $checkPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $checkPen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    
    $checkPoints = @(
        (New-Object System.Drawing.Point([int](360 * $scale), [int](140 * $scale))),
        (New-Object System.Drawing.Point([int](380 * $scale), [int](160 * $scale))),
        (New-Object System.Drawing.Point([int](420 * $scale), [int](115 * $scale)))
    )
    $graphics.DrawLines($checkPen, $checkPoints)
    
    # Cleanup
    $graphics.Dispose()
    
    # Save
    $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    
    Write-Host "Created: $OutputPath ($Size x $Size)"
}

# Generate all required sizes
$sizes = @{
    "Square44x44Logo.scale-100" = 44
    "Square44x44Logo.scale-125" = 55
    "Square44x44Logo.scale-150" = 66
    "Square44x44Logo.scale-200" = 88
    "Square44x44Logo.scale-400" = 176
    "Square44x44Logo.targetsize-16" = 16
    "Square44x44Logo.targetsize-24" = 24
    "Square44x44Logo.targetsize-24_altform-unplated" = 24
    "Square44x44Logo.targetsize-32" = 32
    "Square44x44Logo.targetsize-48" = 48
    "Square44x44Logo.targetsize-256" = 256
    "Square150x150Logo.scale-100" = 150
    "Square150x150Logo.scale-125" = 188
    "Square150x150Logo.scale-150" = 225
    "Square150x150Logo.scale-200" = 300
    "Square150x150Logo.scale-400" = 600
    "Wide310x150Logo.scale-100" = 310  # Will need special handling
    "Wide310x150Logo.scale-200" = 620
    "LockScreenLogo.scale-200" = 48
    "SplashScreen.scale-200" = 620  # Will need special handling
    "StoreLogo.scale-100" = 50
    "StoreLogo.scale-125" = 63
    "StoreLogo.scale-150" = 75
    "StoreLogo.scale-200" = 100
    "StoreLogo.scale-400" = 200
}

foreach ($item in $sizes.GetEnumerator()) {
    $outputPath = Join-Path $assetsPath "$($item.Key).png"
    Create-Icon -Size $item.Value -OutputPath $outputPath
}

# Create ICO file for Windows Explorer/Desktop
Write-Host "`nCreating ICO file..."

# ICO sizes: 16, 24, 32, 48, 64, 128, 256
$icoSizes = @(16, 24, 32, 48, 64, 128, 256)
$icoPath = Join-Path $assetsPath "JobTracker.ico"

# Create individual PNGs for ICO
$icoPngs = @()
foreach ($size in $icoSizes) {
    $tempPath = Join-Path $assetsPath "temp_ico_$size.png"
    Create-Icon -Size $size -OutputPath $tempPath
    $icoPngs += $tempPath
}

# Use magick if available, otherwise provide instructions
$magickPath = Get-Command "magick" -ErrorAction SilentlyContinue

if ($magickPath) {
    $args = $icoPngs + @($icoPath)
    & magick $args
    Write-Host "Created: $icoPath"
} else {
    Write-Host "`nNote: ImageMagick not found. To create ICO file manually:"
    Write-Host "1. Use an online converter like https://icoconvert.com/"
    Write-Host "2. Or install ImageMagick and run: magick $($icoPngs -join ' ') $icoPath"
}

# Cleanup temp files
foreach ($temp in $icoPngs) {
    if (Test-Path $temp) {
        Remove-Item $temp -Force
    }
}

Write-Host "`nIcon generation complete!"
