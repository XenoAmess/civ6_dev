// Deterministic layout of the selected source art; no character generation.
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

internal static class BaiqiArtLayout
{
    private static void DrawFit(Graphics graphics, Image source, RectangleF target, bool cover)
    {
        float sx = target.Width / source.Width, sy = target.Height / source.Height;
        float scale = cover ? Math.Max(sx, sy) : Math.Min(sx, sy);
        RectangleF fitted = new RectangleF(
            target.X + (target.Width - source.Width * scale) / 2,
            target.Y + (target.Height - source.Height * scale) / 2,
            source.Width * scale, source.Height * scale);
        GraphicsState state = graphics.Save();
        try
        {
            graphics.SetClip(target, CombineMode.Intersect);
            using (ImageAttributes attributes = new ImageAttributes())
            {
                attributes.SetWrapMode(WrapMode.TileFlipXY);
                graphics.DrawImage(source, Rectangle.Round(fitted), 0, 0,
                    source.Width, source.Height, GraphicsUnit.Pixel, attributes);
            }
        }
        finally { graphics.Restore(state); }
    }

    private static void Canvas(string path, int width, int height, bool opaque, Action<Graphics> draw)
    {
        using (Bitmap bitmap = new Bitmap(width, height, PixelFormat.Format32bppArgb))
        using (Graphics graphics = Graphics.FromImage(bitmap))
        {
            graphics.Clear(opaque ? Color.Black : Color.Transparent);
            graphics.CompositingMode = CompositingMode.SourceOver;
            graphics.CompositingQuality = CompositingQuality.HighQuality;
            graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
            draw(graphics);
            bitmap.Save(path, ImageFormat.Png);
        }
    }

    private static int Main(string[] args)
    {
        if (args.Length != 2) { Console.Error.WriteLine("Usage: BaiqiArtLayout source-kit output-directory"); return 2; }
        string kit = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[1]);
        Directory.CreateDirectory(output);
        using (Image portrait = Image.FromFile(Path.Combine(kit, "portrait-master.png")))
        using (Image leader = Image.FromFile(Path.Combine(kit, "leader-master.png")))
        using (Image background = Image.FromFile(Path.Combine(kit, "background-master.png")))
        {
            foreach (int size in new int[] { 32, 45, 50, 55, 64, 80, 256 })
            {
                int dimension = size;
                Canvas(Path.Combine(output, "Baiqi_Leader" + size + ".png"), size, size, false,
                    delegate(Graphics graphics) {
                        DrawFit(graphics, portrait, new RectangleF(dimension * .04f, dimension * .04f,
                            dimension * .92f, dimension * .92f), false);
                    });
            }
            Canvas(Path.Combine(output, "Baiqi_SelectionForeground.png"), 825, 1024, false,
                delegate(Graphics graphics) { DrawFit(graphics, leader, new RectangleF(-90, 190, 825, 800), false); });
            Canvas(Path.Combine(output, "Baiqi_LeaderForeground.png"), 825, 1024, false,
                delegate(Graphics graphics) { DrawFit(graphics, leader, new RectangleF(20, 190, 825, 720), false); });
            Canvas(Path.Combine(output, "Baiqi_LoadingBackground.png"), 1920, 960, true,
                delegate(Graphics graphics) { DrawFit(graphics, background, new RectangleF(0, 0, 1920, 960), true); });
            Canvas(Path.Combine(output, "Baiqi_DiplomacyBackground.png"), 1920, 1010, true,
                delegate(Graphics graphics) {
                    DrawFit(graphics, background, new RectangleF(0, 0, 1920, 1010), true);
                    float height = 1470, width = height * leader.Width / leader.Height;
                    DrawFit(graphics, leader, new RectangleF(885, 10, width, height), false);
                });
        }
        Console.WriteLine("Exported 11 source-preserving PNG layouts.");
        return 0;
    }
}
