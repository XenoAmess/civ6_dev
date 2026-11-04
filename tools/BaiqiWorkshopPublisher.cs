// Uses the official Civ6 SDK's Steamworks.NET assembly; no SDK binaries are shipped.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using Microsoft.Win32;
using Steamworks;

public static class BaiqiWorkshopPublisher {
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
    static readonly AppId_t Consumer = new AppId_t(289070);
    static string Journal;
    static Dictionary<string, object> Config;
    static uint RunningApp;
    static List<string> LastPreviewNames = new List<string>();
    static int ExpectedPreviews() { return Config.ContainsKey("expected_previews") ? Convert.ToInt32(Config["expected_previews"]) : 2; }
    static string Text(string key) { return (string)Config[key]; }
    [DllImport("CSteamworks", CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    static extern bool ISteamUGC_GetQueryUGCResult(UGCQueryHandle_t handle, uint index, IntPtr details);
    static string Utf8Field(IntPtr buffer, string name) {
        var field = typeof(SteamUGCDetails_t).GetField(name);
        var attribute = (MarshalAsAttribute)field.GetCustomAttributes(typeof(MarshalAsAttribute), false)[0];
        int offset = Marshal.OffsetOf(typeof(SteamUGCDetails_t), name).ToInt32();
        byte[] bytes = new byte[attribute.SizeConst];
        Marshal.Copy(IntPtr.Add(buffer, offset), bytes, 0, bytes.Length);
        int count = Array.IndexOf(bytes, (byte)0);
        Require(count >= 0, "Unterminated native UTF-8 field");
        return new UTF8Encoding(false, true).GetString(bytes, 0, count);
    }
    static bool QueryDetails(UGCQueryHandle_t query, uint index, out SteamUGCDetails_t item) {
        if (!SteamUGC.GetQueryUGCResult(query, index, out item)) return false;
        // The old official SDK marshals fixed char[] fields using Windows ANSI.
        // Use its exact struct offsets/size to read these UTF-8 fields without lossy ANSI conversion.
        IntPtr buffer = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(SteamUGCDetails_t)));
        try {
            Require(ISteamUGC_GetQueryUGCResult(query, index, buffer), "Native UTF-8 query failed");
            item.m_rgchTitle = Utf8Field(buffer, "m_rgchTitle");
            item.m_rgchDescription = Utf8Field(buffer, "m_rgchDescription");
            item.m_rgchTags = Utf8Field(buffer, "m_rgchTags");
            return true;
        } finally { Marshal.FreeHGlobal(buffer); }
    }
    static void Require(bool ok, string message) { if (!ok) throw new InvalidOperationException(message); }
    static void Record(string name, object data) {
        string path = Path.Combine(Journal, name + ".json");
        using (var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
        using (var writer = new StreamWriter(file, new System.Text.UTF8Encoding(false))) {
            writer.WriteLine(Json.Serialize(data)); writer.Flush(); file.Flush(true);
        }
    }
    static void Emit(string stage, object data) {
        Console.WriteLine(Json.Serialize(new { utc = DateTime.UtcNow.ToString("o"), stage, data }));
        Console.Out.Flush();
    }
    static T Await<T>(SteamAPICall_t call, string name) where T : struct {
        bool done = false, failed = false; T value = default(T);
        var result = CallResult<T>.Create((v, ioFailure) => { value = v; failed = ioFailure; done = true; });
        try {
            result.Set(call);
            var start = DateTime.UtcNow; int reported = 0;
            while (!done && (DateTime.UtcNow - start).TotalSeconds < 240) {
                SteamAPI.RunCallbacks();
                int seconds = (int)(DateTime.UtcNow - start).TotalSeconds;
                if (seconds >= reported + 10) { reported = seconds; Emit(name + "_waiting", new { seconds }); }
                Thread.Sleep(100);
            }
        } finally { result.Cancel(); GC.KeepAlive(result); }
        Require(done, name + " result unknown: timeout; never replay this mutation automatically");
        Require(!failed, name + " I/O failure; inspect journal before any further mutation");
        return value;
    }
    static void Session() {
        Require(SteamUser.BLoggedOn(), "Steam session is not connected; no login/override attempted");
        Require(SteamUtils.GetAppID().m_AppId == RunningApp, "Unexpected current Steam app context");
        uint expected;
        using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam\ActiveProcess")) {
            Require(key != null, "No current Steam account binding");
            expected = unchecked((uint)Convert.ToInt32(key.GetValue("ActiveUser")));
        }
        Require(expected != 0 && SteamUser.GetSteamID().GetAccountID().m_AccountID == expected,
                "Active Steam account mismatch; stop without login");
        Emit("session_bound", new { running_app = RunningApp, creator_app = 404350, consumer_app = 289070, account_match = true });
    }
    static List<SteamUGCDetails_t> Published() {
        var items = new List<SteamUGCDetails_t>();
        for (uint page = 1; page <= 100; page++) {
            var query = SteamUGC.CreateQueryUserUGCRequest(SteamUser.GetSteamID().GetAccountID(),
                EUserUGCList.k_EUserUGCList_Published, EUGCMatchingUGCType.k_EUGCMatchingUGCType_All,
                EUserUGCListSortOrder.k_EUserUGCListSortOrder_CreationOrderDesc,
                new AppId_t(404350), Consumer, page);
            Require(SteamUGC.SetReturnLongDescription(query, true), "SetReturnLongDescription failed");
            try {
                var result = Await<SteamUGCQueryCompleted_t>(SteamUGC.SendQueryUGCRequest(query), "query");
                Require(result.m_eResult == EResult.k_EResultOK, "Published-item query failed: " + result.m_eResult);
                for (uint i = 0; i < result.m_unNumResultsReturned; i++) {
                    SteamUGCDetails_t item;
                    Require(QueryDetails(query, i, out item), "Failed reading published item");
                    Require(item.m_eResult == EResult.k_EResultOK && item.m_nConsumerAppID.m_AppId == 289070 &&
                            item.m_ulSteamIDOwner == SteamUser.GetSteamID().m_SteamID, "Unexpected item identity");
                    items.Add(item);
                }
                if (items.Count >= result.m_unTotalMatchingResults) return items;
                Require(result.m_unNumResultsReturned > 0, "Incomplete published-item enumeration");
            } finally { SteamUGC.ReleaseQueryUGCRequest(query); }
        }
        throw new InvalidOperationException("Published-item query exceeded page budget");
    }
    static SteamUGCDetails_t Details(PublishedFileId_t id, bool verifyFull) {
        var query = SteamUGC.CreateQueryUGCDetailsRequest(new PublishedFileId_t[] { id }, 1);
        Require(SteamUGC.SetReturnLongDescription(query, true), "Long description query refused");
        Require(SteamUGC.SetReturnAdditionalPreviews(query, true), "Additional preview query refused");
        Require(SteamUGC.SetAllowCachedResponse(query, 0), "Fresh details query refused");
        try {
            var result = Await<SteamUGCQueryCompleted_t>(SteamUGC.SendQueryUGCRequest(query), "details");
            Require(result.m_eResult == EResult.k_EResultOK && result.m_unNumResultsReturned == 1, "Details query failed");
            SteamUGCDetails_t item;
            Require(QueryDetails(query, 0, out item), "Details read failed");
            Require(item.m_eResult == EResult.k_EResultOK && item.m_nPublishedFileId == id &&
                    item.m_nConsumerAppID.m_AppId == 289070 && item.m_ulSteamIDOwner == SteamUser.GetSteamID().m_SteamID,
                    "Workshop item ownership/consumer mismatch");
            uint previews = SteamUGC.GetQueryUGCNumAdditionalPreviews(query, 0);
            var media = new List<object>();
            LastPreviewNames = new List<string>();
            for (uint i = 0; i < previews; i++) {
                string url, original; EItemPreviewType type;
                Require(SteamUGC.GetQueryUGCAdditionalPreview(query, 0, i, out url, 4096, out original, 1024, out type), "Preview read failed");
                media.Add(new { index = i, url, original, type = type.ToString() });
                LastPreviewNames.Add(original);
            }
            Emit("item_readback", new { published_file_id = id.m_PublishedFileId, visibility = item.m_eVisibility.ToString(),
                title = item.m_rgchTitle, description_matches = item.m_rgchDescription == Text("description"), cached = result.m_bCachedData,
                content_bytes = item.m_nFileSize, primary_preview_bytes = item.m_nPreviewFileSize, tags = item.m_rgchTags, additional_previews = media });
            if (verifyFull) {
                Require(item.m_rgchTitle == Text("title"), "Remote title differs");
                Require(item.m_rgchDescription == Text("description"), "Remote description differs");
                Require(previews == ExpectedPreviews(), "Unexpected gameplay gallery preview count");
                Require(item.m_nFileSize > 0 && item.m_nPreviewFileSize > 0, "No content/primary preview bytes");
            }
            return item;
        } finally { SteamUGC.ReleaseQueryUGCRequest(query); }
    }
    static PublishedFileId_t CreateDraft() {
        var items = Published();
        Require(!items.Any(i => i.m_rgchTitle.Contains("白绮") || i.m_rgchDescription.Contains(Text("mod_id"))),
                "Potential existing Baiqi item; inspect and update by known ID, do not create a duplicate");
        Record("create-intent", new { utc = DateTime.UtcNow.ToString("o"), consumer_app = 289070, mod_id = Text("mod_id"), existing_item_count = items.Count });
        var created = Await<CreateItemResult_t>(SteamUGC.CreateItem(Consumer, EWorkshopFileType.k_EWorkshopFileTypeCommunity), "create");
        Record("create-result", new { result = created.m_eResult.ToString(), published_file_id = created.m_nPublishedFileId.m_PublishedFileId,
            needs_legal_agreement = created.m_bUserNeedsToAcceptWorkshopLegalAgreement });
        Require(created.m_eResult == EResult.k_EResultOK, "CreateItem failed: " + created.m_eResult);
        Require(created.m_nPublishedFileId.m_PublishedFileId != 0, "Missing created item ID");
        Emit("created_item", new { published_file_id = created.m_nPublishedFileId.m_PublishedFileId });
        Require(!created.m_bUserNeedsToAcceptWorkshopLegalAgreement, "Workshop legal agreement requires the user; no terms accepted by this tool");
        return created.m_nPublishedFileId;
    }
    static void Draft(PublishedFileId_t id) {
        Session(); Details(id, false);
        var update = SteamUGC.StartItemUpdate(Consumer, id);
        Require(SteamUGC.SetItemTitle(update, Text("title")), "Set title failed");
        Require(SteamUGC.SetItemDescription(update, Text("description")), "Set description failed");
        Require(SteamUGC.SetItemMetadata(update, Text("mod_id")), "Set mod ID metadata failed");
        Require(SteamUGC.SetItemVisibility(update, ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPrivate), "Set private failed");
        Require(SteamUGC.SetItemTags(update, new List<string> { "AI", "Gameplay", "Leaders", "Gathering Storm" }), "Set tags failed");
        Require(SteamUGC.SetItemContent(update, Text("content")), "Set content failed");
        Require(SteamUGC.SetItemPreview(update, Text("preview")), "Set primary preview failed");
        Require(SteamUGC.AddItemPreviewFile(update, Text("overview"), EItemPreviewType.k_EItemPreviewType_Image), "Add gameplay overview failed");
        Require(SteamUGC.AddItemPreviewFile(update, Text("city"), EItemPreviewType.k_EItemPreviewType_Image), "Add gameplay city failed");
        Record("draft-submit-intent", new { utc = DateTime.UtcNow.ToString("o"), published_file_id = id.m_PublishedFileId, visibility = "private", product_files = 87, additional_previews = 2 });
        var result = Await<SubmitItemUpdateResult_t>(SteamUGC.SubmitItemUpdate(update, Text("change_notes")), "draft_submit");
        Record("draft-submit-result", new { result = result.m_eResult.ToString(), needs_legal_agreement = result.m_bUserNeedsToAcceptWorkshopLegalAgreement });
        Require(result.m_eResult == EResult.k_EResultOK && !result.m_bUserNeedsToAcceptWorkshopLegalAgreement, "Draft update failed or requires legal agreement: " + result.m_eResult);
        Details(id, true);
    }
    static void Publish(PublishedFileId_t id) {
        Session(); Details(id, true);
        var update = SteamUGC.StartItemUpdate(Consumer, id);
        Require(SteamUGC.SetItemVisibility(update, ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPublic), "Set public failed");
        Record("public-submit-intent", new { utc = DateTime.UtcNow.ToString("o"), published_file_id = id.m_PublishedFileId });
        var result = Await<SubmitItemUpdateResult_t>(SteamUGC.SubmitItemUpdate(update, null), "publish");
        Record("public-submit-result", new { result = result.m_eResult.ToString(), needs_legal_agreement = result.m_bUserNeedsToAcceptWorkshopLegalAgreement });
        Require(result.m_eResult == EResult.k_EResultOK && !result.m_bUserNeedsToAcceptWorkshopLegalAgreement, "Public update failed or requires agreement");
        var item = Details(id, true);
        Require(item.m_eVisibility == ERemoteStoragePublishedFileVisibility.k_ERemoteStoragePublishedFileVisibilityPublic, "Item not public in SDK readback");
    }
    static void Download(PublishedFileId_t id) {
        Session(); Details(id, true);
        bool done = false; DownloadItemResult_t result = default(DownloadItemResult_t);
        var callback = Callback<DownloadItemResult_t>.Create(value => {
            if (value.m_nPublishedFileId == id) { result = value; done = true; }
        });
        try {
            Record("download-intent", new { utc = DateTime.UtcNow.ToString("o"), published_file_id = id.m_PublishedFileId, high_priority = false, subscribe = false });
            Require(SteamUGC.DownloadItem(id, false), "Workshop verification download refused; no subscription or priority override");
            var start = DateTime.UtcNow;
            while (!done && (DateTime.UtcNow - start).TotalSeconds < 240) { SteamAPI.RunCallbacks(); Thread.Sleep(100); }
            Emit("download_callback", new { received = done, app_id = result.m_unAppID.m_AppId, result = result.m_eResult.ToString() });
            Require(done && result.m_unAppID.m_AppId == 289070 && result.m_eResult == EResult.k_EResultOK, "Download callback unavailable/failed; no installation verification claim");
            ulong size; string folder; uint timestamp;
            Require(SteamUGC.GetItemInstallInfo(id, out size, out folder, 4096, out timestamp), "No downloaded install information");
            Record("download-result", new { result = result.m_eResult.ToString(), published_file_id = id.m_PublishedFileId, bytes = size, folder, timestamp });
            Emit("download_complete", new { published_file_id = id.m_PublishedFileId, bytes = size, folder, timestamp });
        } finally { callback.Unregister(); GC.KeepAlive(callback); }
    }
    static void UpdatePage(PublishedFileId_t id) {
        Session(); Details(id, false);
        Require(LastPreviewNames.Count == ExpectedPreviews(), "Complete gallery must be uploaded before changing page");
        var update = SteamUGC.StartItemUpdate(Consumer, id);
        Require(SteamUGC.SetItemTitle(update, Text("title")), "Set page title failed");
        Require(SteamUGC.SetItemDescription(update, Text("description")), "Set page description failed");
        Record("page-revision2-submit-intent", new { utc = DateTime.UtcNow.ToString("o"), published_file_id = id.m_PublishedFileId, images_in_body = ExpectedPreviews(), content_changed = false });
        var result = Await<SubmitItemUpdateResult_t>(SteamUGC.SubmitItemUpdate(update, Text("change_notes")), "page_update");
        Record("page-revision2-submit-result", new { result = result.m_eResult.ToString(), needs_legal_agreement = result.m_bUserNeedsToAcceptWorkshopLegalAgreement });
        Require(result.m_eResult == EResult.k_EResultOK && !result.m_bUserNeedsToAcceptWorkshopLegalAgreement, "Page update failed or needs agreement");
        Details(id, true);
    }
    static void AppendOnePreview(PublishedFileId_t id) {
        Session(); Details(id, false);
        var paths = ((System.Collections.IEnumerable)Config["new_gallery"]).Cast<object>().Select(Convert.ToString).ToList();
        var allowed = new List<string> { "overview.jpg", "city-readonly.jpg" }; allowed.AddRange(paths.Select(Path.GetFileName));
        Require(paths.Count == 5 && paths.All(File.Exists) && LastPreviewNames.Distinct().Count() == LastPreviewNames.Count &&
                LastPreviewNames.All(allowed.Contains), "Unexpected gallery contents; no automatic alteration");
        string next = paths.FirstOrDefault(path => !LastPreviewNames.Contains(Path.GetFileName(path)));
        if (next == null) { Require(LastPreviewNames.Count == 7, "Unexpected final gallery count"); Emit("gallery_complete", new { images = 7 }); return; }
        int previous = LastPreviewNames.Count; string name = Path.GetFileNameWithoutExtension(next);
        Require(System.Text.RegularExpressions.Regex.IsMatch(name, "^page2-[a-z0-9-]+$"), "Unexpected preview staging filename");
        var update = SteamUGC.StartItemUpdate(Consumer, id);
        Require(SteamUGC.AddItemPreviewFile(update, next, EItemPreviewType.k_EItemPreviewType_Image), "Append preview refused");
        Record(name + "-submit-intent", new { utc = DateTime.UtcNow.ToString("o"), published_file_id = id.m_PublishedFileId, preview = name, previous_count = previous, content_changed = false });
        var result = Await<SubmitItemUpdateResult_t>(SteamUGC.SubmitItemUpdate(update, null), "append_preview");
        Record(name + "-submit-result", new { result = result.m_eResult.ToString(), needs_legal_agreement = result.m_bUserNeedsToAcceptWorkshopLegalAgreement });
        Require(result.m_eResult == EResult.k_EResultOK && !result.m_bUserNeedsToAcceptWorkshopLegalAgreement, "Single preview update failed; inspect receipt before retry");
        Details(id, false); Require(LastPreviewNames.Count == previous + 1 && LastPreviewNames.Contains(Path.GetFileName(next)), "Single preview readback differs");
    }
    public static int Main(string[] args) {
        Console.OutputEncoding = new System.Text.UTF8Encoding(false);
        bool initialized = false;
        try {
            Require(args.Length >= 3, "Expected config.json, journal directory, mode, optional item ID");
            Config = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(args[0])); Journal = args[1];
            Require(Directory.Exists(Journal), "Journal directory must already exist");
            Require(Text("remote_occupancy_source") == "user_explicit_idle", "No remote-occupancy user confirmation; do not initialize Steam");
            RunningApp = args[2] == "download" ? 289070U : 404350U;
            Require(Environment.GetEnvironmentVariable("SteamAppId") == RunningApp.ToString(), "Expected explicit SDK/consumer app environment");
            Require(SteamAPI.Init(), "Official SDK SteamAPI.Init failed; no forced login"); initialized = true; Session();
            if (args[2] == "list") { var list = Published(); Emit("own_items_listed", new { count = list.Count, baiqi_matches = list.Count(i => i.m_rgchTitle.Contains("白绮")) }); }
            else if (args[2] == "create-draft") { var id = CreateDraft(); Draft(id); }
            else {
                Require(args.Length == 4, "Explicit existing item ID required"); var id = new PublishedFileId_t(UInt64.Parse(args[3]));
                if (args[2] == "publish") Publish(id);
                else if (args[2] == "readback") Details(id, true);
                else if (args[2] == "inspect") Details(id, false);
                else if (args[2] == "download") Download(id);
                else if (args[2] == "update-page") UpdatePage(id);
                else if (args[2] == "append-preview") AppendOnePreview(id);
                else throw new InvalidOperationException("Unknown mode; refusing mutation");
            }
            return 0;
        } catch (Exception e) { Emit("stopped", new { error = e.Message, no_login_or_replay = true }); return 1; }
        finally { if (initialized) SteamAPI.Shutdown(); }
    }
}
