param(
  [string]$FramesDir = "docs/media/frames",
  [string]$OutputPath = "docs/media/treeroute-demo.gif"
)

Add-Type -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.Serialization;

public static class GifBuilder {
  public static void SaveAnimatedGif(string outputPath, string[] inputPaths, int[] delays) {
    Bitmap first = (Bitmap)Image.FromFile(inputPaths[0]);
    try {
      ImageCodecInfo encoder = GetEncoder(ImageFormat.Gif);
      EncoderParameters ep = new EncoderParameters(1);
      try {
        SetMetadata(first, delays, 0);
        ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.SaveFlag, (long)EncoderValue.MultiFrame);
        first.Save(outputPath, encoder, ep);

        for (int i = 1; i < inputPaths.Length; i++) {
          Bitmap frame = (Bitmap)Image.FromFile(inputPaths[i]);
          try {
            ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.SaveFlag, (long)EncoderValue.FrameDimensionTime);
            first.SaveAdd(frame, ep);
          } finally {
            frame.Dispose();
          }
        }

        ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.SaveFlag, (long)EncoderValue.Flush);
        first.SaveAdd(ep);
      } finally {
        ep.Dispose();
      }
    } finally {
      first.Dispose();
    }
  }

  static void SetMetadata(Image image, int[] delays, ushort loopCount) {
    PropertyItem frameDelay = (PropertyItem)FormatterServices.GetUninitializedObject(typeof(PropertyItem));
    frameDelay.Id = 0x5100;
    frameDelay.Type = 4;
    frameDelay.Len = delays.Length * 4;
    frameDelay.Value = new byte[frameDelay.Len];
    for (int i = 0; i < delays.Length; i++) {
      Array.Copy(BitConverter.GetBytes(delays[i]), 0, frameDelay.Value, i * 4, 4);
    }
    image.SetPropertyItem(frameDelay);

    PropertyItem loop = (PropertyItem)FormatterServices.GetUninitializedObject(typeof(PropertyItem));
    loop.Id = 0x5101;
    loop.Type = 3;
    loop.Len = 2;
    loop.Value = BitConverter.GetBytes(loopCount);
    image.SetPropertyItem(loop);
  }

  static ImageCodecInfo GetEncoder(ImageFormat format) {
    foreach (ImageCodecInfo codec in ImageCodecInfo.GetImageEncoders()) {
      if (codec.FormatID == format.Guid) return codec;
    }
    throw new InvalidOperationException("GIF encoder not found.");
  }
}
'@ -ReferencedAssemblies System.Drawing

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")).Path
$resolvedFramesDir = Join-Path $root $FramesDir
$resolvedOutputPath = Join-Path $root $OutputPath

$orderedFrames = @(
  @{ Path = (Join-Path $resolvedFramesDir "01-home.png"); Delay = 140 },
  @{ Path = (Join-Path $resolvedFramesDir "02-home-filled.png"); Delay = 110 },
  @{ Path = (Join-Path $resolvedFramesDir "03-register.png"); Delay = 120 },
  @{ Path = (Join-Path $resolvedFramesDir "04-planner-prefilled.png"); Delay = 110 },
  @{ Path = (Join-Path $resolvedFramesDir "05-planner-results.png"); Delay = 180 }
)

foreach ($frame in $orderedFrames) {
  if (-not (Test-Path $frame.Path)) {
    throw "Missing frame: $($frame.Path)"
  }
}

$outputDir = Split-Path -Parent $resolvedOutputPath
New-Item -ItemType Directory -Force $outputDir | Out-Null

[GifBuilder]::SaveAnimatedGif(
  $resolvedOutputPath,
  [string[]]($orderedFrames | ForEach-Object { $_.Path }),
  [int[]]($orderedFrames | ForEach-Object { $_.Delay })
)

Write-Output "Created $resolvedOutputPath"
