// Reflection calls pure local helpers only. Never call publisher Main or SteamAPI.Init.
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

public static class WorkshopOfflineTests {
    static readonly Type Publisher = typeof(BaiqiWorkshopPublisher);
    static readonly BindingFlags PrivateStatic = BindingFlags.NonPublic | BindingFlags.Static;
    static int Cases;
    static object Call(string name, params object[] args) {
        try { return Publisher.GetMethod(name, PrivateStatic).Invoke(null, args); }
        catch (TargetInvocationException e) { throw e.InnerException; }
    }
    static void Set(string name, object value) { Publisher.GetField(name, PrivateStatic).SetValue(null, value); }
    static void Check(bool condition, string name) { if (!condition) throw new Exception(name); Cases++; }
    static void Reject(Action action, string name) {
        bool rejected = false;
        try { action(); } catch (InvalidOperationException) { rejected = true; }
        Check(rejected, name);
    }
    public static int Main(string[] args) {
        try {
            string root = Path.GetFullPath(args[0]);
            if (!Directory.Exists(root)) throw new Exception("Fixture directory must already exist");
            var paths = Enumerable.Range(0, 8).Select(i => Path.Combine(root,
                (i < 5 ? "page2-" : "page3-") + "image" + i + ".jpg")).ToArray();
            foreach (string path in paths) File.WriteAllText(path, "local-fixture");
            var config = new Dictionary<string, object> { { "product_files", 93 }, { "expected_previews", 7 },
                { "new_gallery", paths.Take(5).ToArray() } };
            var remote = new List<string> { "overview.jpg", "city-readonly.jpg" };
            Set("Config", config); Set("LastPreviewNames", remote);
            Check((int)Call("ProductFiles") == 93, "Verified product count");
            foreach (object bad in new object[] { 0, -1, true, "93", 93.0 }) {
                config["product_files"] = bad; Reject(() => Call("ProductFiles"), "Untyped count rejected");
            }
            config.Remove("product_files"); Reject(() => Call("ProductFiles"), "Missing count rejected");
            config["product_files"] = 93;
            Check((string)Call("NextGalleryPreview") == paths[0], "Legacy gallery first missing");
            remote.AddRange(paths.Take(5).Select(Path.GetFileName));
            Check(Call("NextGalleryPreview") == null, "Legacy seven complete");
            config["expected_previews"] = 10; config["new_gallery"] = paths;
            Check((string)Call("NextGalleryPreview") == paths[5], "Existing seven retained, append eighth");
            remote.Add(Path.GetFileName(paths[5]));
            Check((string)Call("NextGalleryPreview") == paths[6], "Readback next missing");
            remote.AddRange(paths.Skip(6).Select(Path.GetFileName));
            Check(Call("NextGalleryPreview") == null, "Ten complete");
            remote.Add(remote[0]); Reject(() => Call("NextGalleryPreview"), "Duplicate remote rejected"); remote.RemoveAt(remote.Count - 1);
            remote[0] = "unknown.jpg"; Reject(() => Call("NextGalleryPreview"), "Unknown remote rejected"); remote[0] = "overview.jpg";
            remote.RemoveAt(0); Reject(() => Call("NextGalleryPreview"), "Missing base image rejected"); remote.Insert(0, "overview.jpg");
            config["expected_previews"] = 9; Reject(() => Call("NextGalleryPreview"), "Mismatched count rejected"); config["expected_previews"] = 10;
            config["new_gallery"] = paths.Concat(new [] { paths[0] }).ToArray();
            Reject(() => Call("NextGalleryPreview"), "Duplicate local inventory rejected"); config["new_gallery"] = paths;
            string saved = paths[7]; paths[7] = Path.Combine(root, "bad.jpg"); File.WriteAllText(paths[7], "fixture");
            Reject(() => Call("NextGalleryPreview"), "Wrong local filename rejected"); paths[7] = saved;
            File.Delete(paths[7]); Reject(() => Call("NextGalleryPreview"), "Missing local file rejected");
            Set("Journal", root); Call("Record", "content-submit-intent", new { sample = "first" });
            string receipt = Path.Combine(root, "content-submit-intent.json"); string first = File.ReadAllText(receipt);
            bool replayRefused = false;
            try { Call("Record", "content-submit-intent", new { sample = "second" }); } catch (IOException) { replayRefused = true; }
            Check(replayRefused && first == File.ReadAllText(receipt), "Exclusive journal preserves first intent");
            Console.WriteLine("WORKSHOP_OFFLINE_HELPERS_PASS cases=" + Cases + " steam_api_initialized=false publisher_main_called=false");
            return 0;
        } catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
}
