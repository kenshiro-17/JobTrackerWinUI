// Simple ICO file creator for Job Tracker
// Run with: dotnet script CreateIco.csx

using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Collections.Generic;

var assetsPath = Path.GetDirectoryName(Environment.GetCommandLineArgs()[0]) ?? ".";
var icoPath = Path.Combine(assetsPath, "JobTracker.ico");

// ICO sizes
var sizes = new[] { 16, 24, 32, 48, 64, 128, 256 };
var images = new List<Bitmap>();

foreach (var size in sizes)
{
    var bitmap = CreateIcon(size);
    images.Add(bitmap);
}

// Write ICO file
using (var fs = new FileStream(icoPath, FileMode.Create))
using (var bw = new BinaryWriter(fs))
{
    // ICO header
    bw.Write((short)0);           // Reserved
    bw.Write((short)1);           // Type: 1 = ICO
    bw.Write((short)images.Count); // Number of images

    var offset = 6 + (16 * images.Count); // Header + entries
    var imageData = new List<byte[]>();

    // Write directory entries
    for (int i = 0; i < images.Count; i++)
    {
        var img = images[i];
        using var ms = new MemoryStream();
        img.Save(ms, ImageFormat.Png);
        var data = ms.ToArray();
        imageData.Add(data);

        bw.Write((byte)(img.Width >= 256 ? 0 : img.Width));
        bw.Write((byte)(img.Height >= 256 ? 0 : img.Height));
        bw.Write((byte)0);        // Color palette
        bw.Write((byte)0);        // Reserved
        bw.Write((short)1);       // Color planes
        bw.Write((short)32);      // Bits per pixel
        bw.Write(data.Length);    // Size
        bw.Write(offset);         // Offset
        offset += data.Length;
    }

    // Write image data
    foreach (var data in imageData)
    {
        bw.Write(data);
    }
}

Console.WriteLine($"Created: {icoPath}");

// Cleanup
foreach (var img in images)
    img.Dispose();

static Bitmap CreateIcon(int size)
{
    var bitmap = new Bitmap(size, size);
    using var g = Graphics.FromImage(bitmap);
    
    g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
    g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
    
    var scale = size / 512.0f;
    
    // Colors
    var pastelBlue = Color.FromArgb(255, 168, 213, 229);
    var pastelGreen = Color.FromArgb(255, 181, 232, 195);
    var darkColor = Color.FromArgb(255, 26, 26, 46);
    
    // Background gradient
    using var bgBrush = new System.Drawing.Drawing2D.LinearGradientBrush(
        new Point(0, 0), new Point(size, size), pastelBlue, pastelGreen);
    
    // Draw rounded background
    var margin = (int)(16 * scale);
    var bgRect = new Rectangle(margin, margin, size - margin * 2, size - margin * 2);
    var radius = Math.Max(1, (int)(48 * scale));
    
    using var bgPath = CreateRoundedRect(bgRect, radius);
    g.FillPath(bgBrush, bgPath);
    
    // Briefcase body
    using var briefcaseBrush = new SolidBrush(darkColor);
    var bx = (int)(100 * scale);
    var by = (int)(180 * scale);
    var bw = (int)(312 * scale);
    var bh = (int)(200 * scale);
    var br = Math.Max(1, (int)(24 * scale));
    
    var briefcaseRect = new Rectangle(bx, by, bw, bh);
    using var briefcasePath = CreateRoundedRect(briefcaseRect, br);
    g.FillPath(briefcaseBrush, briefcasePath);
    
    // Briefcase handle
    using var handlePen = new Pen(darkColor, Math.Max(1, (int)(28 * scale)));
    handlePen.StartCap = System.Drawing.Drawing2D.LineCap.Round;
    handlePen.EndCap = System.Drawing.Drawing2D.LineCap.Round;
    
    var hx1 = (int)(180 * scale);
    var hx2 = (int)(332 * scale);
    var hy1 = (int)(180 * scale);
    var hy2 = (int)(120 * scale);
    
    g.DrawLine(handlePen, hx1, hy1, hx1, hy2);
    g.DrawLine(handlePen, hx1, hy2, hx2, hy2);
    g.DrawLine(handlePen, hx2, hy2, hx2, hy1);
    
    // Briefcase clasp
    using var claspBrush = new SolidBrush(pastelBlue);
    var cx = (int)(230 * scale);
    var cy = (int)(250 * scale);
    var cw = Math.Max(4, (int)(52 * scale));
    var ch = Math.Max(4, (int)(60 * scale));
    g.FillRectangle(claspBrush, cx, cy, cw, ch);
    
    // Checkmark circle
    using var checkCircleBrush = new SolidBrush(pastelGreen);
    using var checkCirclePen = new Pen(Color.White, Math.Max(1, (int)(8 * scale)));
    var ccx = (int)(390 * scale);
    var ccy = (int)(140 * scale);
    var ccr = (int)(55 * scale);
    if (ccr > 2)
    {
        g.FillEllipse(checkCircleBrush, ccx - ccr, ccy - ccr, ccr * 2, ccr * 2);
        g.DrawEllipse(checkCirclePen, ccx - ccr, ccy - ccr, ccr * 2, ccr * 2);
        
        // Checkmark
        using var checkPen = new Pen(darkColor, Math.Max(1, (int)(14 * scale)));
        checkPen.StartCap = System.Drawing.Drawing2D.LineCap.Round;
        checkPen.EndCap = System.Drawing.Drawing2D.LineCap.Round;
        checkPen.LineJoin = System.Drawing.Drawing2D.LineJoin.Round;
        
        var checkPoints = new Point[] {
            new Point((int)(360 * scale), (int)(140 * scale)),
            new Point((int)(380 * scale), (int)(160 * scale)),
            new Point((int)(420 * scale), (int)(115 * scale))
        };
        g.DrawLines(checkPen, checkPoints);
    }
    
    return bitmap;
}

static System.Drawing.Drawing2D.GraphicsPath CreateRoundedRect(Rectangle rect, int radius)
{
    var path = new System.Drawing.Drawing2D.GraphicsPath();
    var diameter = radius * 2;
    
    if (diameter > rect.Width) diameter = rect.Width;
    if (diameter > rect.Height) diameter = rect.Height;
    
    if (diameter < 2)
    {
        path.AddRectangle(rect);
        return path;
    }
    
    path.AddArc(rect.X, rect.Y, diameter, diameter, 180, 90);
    path.AddArc(rect.Right - diameter, rect.Y, diameter, diameter, 270, 90);
    path.AddArc(rect.Right - diameter, rect.Bottom - diameter, diameter, diameter, 0, 90);
    path.AddArc(rect.X, rect.Bottom - diameter, diameter, diameter, 90, 90);
    path.CloseFigure();
    
    return path;
}
