// ==============================================================================
// Malayalam Movie News Studio - Google Apps Script (Code.gs)
// Handles Google Sheet Data Sync, Web App Interface, and 24/7 Cloud Action Triggers
// ==============================================================================

function doGet(e) {
  if (e && e.parameter && e.parameter.action === "get_data") {
    try {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var result = {};
      var configObj = {};
      var serperKeysList = [];
      var sheets = ss.getSheets();
      for (var i = 0; i < sheets.length; i++) {
        var s = sheets[i];
        var name = s.getName();
        var data = s.getDataRange().getValues();
        if (data.length > 1) {
          var headers = data[0];
          var rows = [];
          for (var r = 1; r < data.length; r++) {
            var rowObj = {};
            for (var c = 0; c < headers.length; c++) {
              rowObj[headers[c]] = data[r][c];
            }
            rows.push(rowObj);
          }
          result[name] = rows;
          
          if (name === "Serper Keys" || name === "Serper_Keys" || name === "SerperKeys" || name === "API Keys") {
            for (var sk = 1; sk < data.length; sk++) {
              var keyVal = String(data[sk][0] || "").trim();
              if (keyVal && keyVal.length >= 20 && serperKeysList.indexOf(keyVal) === -1) {
                serperKeysList.push(keyVal);
              }
            }
          }

          if (name === "Config" || name === "Settings") {
            for (var k = 1; k < data.length; k++) {
              var kname = String(data[k][0] || "").trim().toLowerCase();
              var kval = String(data[k][1] || "").trim();
              if (kname.indexOf("groq") !== -1) {
                configObj["groq_api_key"] = kval;
              }
              if (kname.indexOf("gemini") !== -1) {
                configObj["gemini_api_key"] = kval;
              }
              if (kname.indexOf("serper") !== -1) {
                var sKeys = kval.split(/[\r\n,]+/);
                for (var si = 0; si < sKeys.length; si++) {
                  var skItem = sKeys[si].trim();
                  if (skItem && skItem.length >= 20 && serperKeysList.indexOf(skItem) === -1) {
                    serperKeysList.push(skItem);
                  }
                }
              }
            }
          }
        }
      }

      // Auto-initialize Serper Keys sheet if not yet present
      if (serperKeysList.length === 0) {
        var skSheet = ss.getSheetByName("Serper Keys");
        if (!skSheet) {
          skSheet = ss.insertSheet("Serper Keys");
          skSheet.appendRow(["Serper API Key", "Status", "Added Date"]);
          var defaultKeys = [
            '706d6e0c2e53e2d18b6f85808d560536e5d97ab7',
            '6fd2aecf0e6a8aaba3a1e5c6f3f63d54f6779236',
            '8cc926c37bc6a93c0a28ea9bee6e25b62655b561',
            '9c7b69b58d92d293b000ac9d43c87e736f3809c1',
            'a5e997a31056ecf4653442d3bb0ffde0a9964fc4',
            '32541b9cc4fad4ef33cf2b7353a668c3845de9fc',
            '3e2ceb8660a332263aab5b85434a311fe4f3a82c'
          ];
          for (var dk = 0; dk < defaultKeys.length; dk++) {
            skSheet.appendRow([defaultKeys[dk], "Active", new Date().toISOString().split("T")[0]]);
            serperKeysList.push(defaultKeys[dk]);
          }
        }
      }

      result["config"] = configObj;
      result["serper_keys"] = serperKeysList;

      if (e.parameter.callback) {
        var cb = e.parameter.callback;
        return ContentService.createTextOutput(cb + "(" + JSON.stringify(result) + ");")
          .setMimeType(ContentService.MimeType.JAVASCRIPT);
      }
      return ContentService.createTextOutput(JSON.stringify(result))
        .setMimeType(ContentService.MimeType.JSON);
    } catch (err) {
      if (e.parameter.callback) {
        return ContentService.createTextOutput(e.parameter.callback + "(" + JSON.stringify({"error": err.toString()}) + ");")
          .setMimeType(ContentService.MimeType.JAVASCRIPT);
      }
      return ContentService.createTextOutput(JSON.stringify({"error": err.toString()}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Malayalam Movie News Studio')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // Save Groq API Key if provided in payload
    if (data.groq_api_key) {
      saveConfigSheet("GROQ_API_KEY", data.groq_api_key);
    }

    // Save Gemini API Key if provided in payload
    if (data.gemini_api_key) {
      saveConfigSheet("GEMINI_API_KEY", data.gemini_api_key);
    }

    // 0. Handle Adding Serper API Key to Google Sheet
    if (data.action === "add_serper_key" && data.key) {
      var addedKey = String(data.key).trim();
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var skSheet = ss.getSheetByName("Serper Keys");
      if (!skSheet) {
        skSheet = ss.insertSheet("Serper Keys");
        skSheet.appendRow(["Serper API Key", "Status", "Added Date"]);
      }
      var existingData = skSheet.getDataRange().getValues();
      var exists = false;
      for (var ek = 1; ek < existingData.length; ek++) {
        if (String(existingData[ek][0]).trim() === addedKey) {
          exists = true;
          break;
        }
      }
      if (!exists) {
        skSheet.appendRow([addedKey, "Active", new Date().toISOString().split("T")[0]]);
      }
      var allKeys = [];
      var updatedData = skSheet.getDataRange().getValues();
      for (var uk = 1; uk < updatedData.length; uk++) {
        var kVal = String(updatedData[uk][0] || "").trim();
        if (kVal && kVal.length >= 20 && allKeys.indexOf(kVal) === -1) allKeys.push(kVal);
      }
      return ContentService.createTextOutput(JSON.stringify({"status": "success", "serper_keys": allKeys}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 0b. Handle Deleting Serper API Key from Google Sheet
    if (data.action === "delete_serper_key" && data.key) {
      var delKey = String(data.key).trim();
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var skSheet = ss.getSheetByName("Serper Keys");
      if (skSheet) {
        var rowsData = skSheet.getDataRange().getValues();
        for (var rk = rowsData.length - 1; rk >= 1; rk--) {
          if (String(rowsData[rk][0]).trim() === delKey) {
            skSheet.deleteRow(rk + 1);
          }
        }
      }
      var remainingKeys = [];
      if (skSheet) {
        var remData = skSheet.getDataRange().getValues();
        for (var rem = 1; rem < remData.length; rem++) {
          var remVal = String(remData[rem][0] || "").trim();
          if (remVal && remVal.length >= 20) remainingKeys.push(remVal);
        }
      }
      return ContentService.createTextOutput(JSON.stringify({"status": "success", "serper_keys": remainingKeys}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 0c. Handle Video Upload & Metadata Logging to Google Sheets
    if (data.action === "log_video_metadata" || data.action === "log_upload") {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var uploadSheet = ss.getSheetByName("Video Uploads");
      if (!uploadSheet) {
        uploadSheet = ss.insertSheet("Video Uploads");
        uploadSheet.appendRow([
          "Upload Time (IST)",
          "Video Title",
          "YouTube Video URL",
          "Privacy Status",
          "Specific Topic Chapters",
          "Description",
          "Tags"
        ]);
        uploadSheet.setFrozenRows(1);
      }
      
      var nowIST = Utilities.formatDate(new Date(), "Asia/Kolkata", "yyyy-MM-dd HH:mm:ss");
      uploadSheet.appendRow([
        nowIST,
        data.title || "",
        data.video_url || "",
        data.privacy_status || "",
        data.chapters || "",
        data.description || "",
        data.tags || ""
      ]);

      return ContentService.createTextOutput(JSON.stringify({"status": "success", "sheet": "Video Uploads"}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // 1. Handle GitHub Action Trigger Request from Web App / Website
    if (data.action === "trigger_github") {
      if (data.drive_thumbnail_url || data.thumbnail_main_hook) {
        saveThumbnailConfigSheet(
          data.drive_thumbnail_url,
          data.thumbnail_main_hook,
          data.thumbnail_sub_text,
          data.thumbnail_badge,
          data.thumbnail_color_theme,
          data.thumbnail_layout_style
        );
      }
      return triggerGitHubActionHandler(data.privacy_status, data.drive_thumbnail_url, data.token, data.sections);
    }

    // 2. Handle Google Sheet Table Sync Request
    if (data.thumbnail_urls || data.thumbnail_main_hook) {
      saveThumbnailConfigSheet(
        data.thumbnail_urls,
        data.thumbnail_main_hook,
        data.thumbnail_sub_text,
        data.thumbnail_badge,
        data.thumbnail_color_theme,
        data.thumbnail_layout_style
      );
    }

    var tabName = data.tab_name;
    var rows = data.rows;

    if (tabName && rows) {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = ss.getSheetByName(tabName);
      if (!sheet) {
        sheet = ss.insertSheet(tabName);
      }

      // Clear old data and set headers based on worksheet category
      sheet.clearContents();
      
      if (tabName === "OTT Updates") {
        sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date", "OTT Platform"]);
        for (var i = 0; i < rows.length; i++) {
          var r = rows[i];
          sheet.appendRow([
            r["Topic Number"] || "",
            r["Malayalam News Text"] || "",
            r["Image URLs"] || "",
            r["Topic Headline"] || r["Movie Name"] || "",
            r["Release Date"] || "",
            r["OTT Platform"] || ""
          ]);
        }
      } else if (tabName === "Release Updates") {
        sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date"]);
        for (var i = 0; i < rows.length; i++) {
          var r = rows[i];
          sheet.appendRow([
            r["Topic Number"] || "",
            r["Malayalam News Text"] || "",
            r["Image URLs"] || "",
            r["Topic Headline"] || r["Movie Name"] || "",
            r["Release Date"] || ""
          ]);
        }
      } else {
        sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline"]);
        for (var i = 0; i < rows.length; i++) {
          var r = rows[i];
          sheet.appendRow([
            r["Topic Number"] || "",
            r["Malayalam News Text"] || "",
            r["Image URLs"] || "",
            r["Topic Headline"] || r["Movie Name"] || ""
          ]);
        }
      }
    }

    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function saveThumbnailConfigSheet(urlsString, mainHook, subText, badge, colorTheme, layoutStyle) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Thumbnail Config");
    if (!sheet) {
      sheet = ss.insertSheet("Thumbnail Config");
    }
    sheet.clearContents();
    sheet.appendRow([
      "Selected Image URLs",
      "Main Hook",
      "Sub Text",
      "Badge Label",
      "Color Theme",
      "Layout Style"
    ]);

    var rawStr = String(urlsString || "");

    // Extract metadata from string if passed as embedded tags
    var mHook = mainHook || (rawStr.match(/__THUMB_HOOK__:([^|]+)/) ? rawStr.match(/__THUMB_HOOK__:([^|]+)/)[1] : "");
    var mSub = subText || (rawStr.match(/__THUMB_SUB__:([^|]+)/) ? rawStr.match(/__THUMB_SUB__:([^|]+)/)[1] : "");
    var mBadge = badge || (rawStr.match(/__THUMB_BADGE__:([^|]+)/) ? rawStr.match(/__THUMB_BADGE__:([^|]+)/)[1] : "");
    var mTheme = colorTheme || (rawStr.match(/__THUMB_THEME__:([^|]+)/) ? rawStr.match(/__THUMB_THEME__:([^|]+)/)[1] : "");
    var mLayout = layoutStyle || (rawStr.match(/__THUMB_LAYOUT__:([^|]+)/) ? rawStr.match(/__THUMB_LAYOUT__:([^|]+)/)[1] : "");

    var cleanUrls = rawStr
      .replace(/\|*__SECTIONS__:[a-zA-Z0-9_,]+/g, '')
      .replace(/\|*__THUMB_[A-Z]+__:[^|]+/g, '')
      .trim();

    var urls = [];
    if (cleanUrls) {
      var parts = cleanUrls.split(/[\r\n,]+/);
      for (var i = 0; i < parts.length; i++) {
        var u = parts[i].trim();
        if (u && u.toLowerCase().indexOf("http") === 0 && urls.indexOf(u) === -1) {
          urls.push(u);
        }
      }
    }

    var firstUrl = urls.length > 0 ? urls[0] : "";
    sheet.appendRow([
      firstUrl,
      mHook || "",
      mSub || "",
      mBadge || "",
      mTheme || "",
      mLayout || ""
    ]);

    for (var j = 1; j < urls.length; j++) {
      sheet.appendRow([urls[j]]);
    }
  } catch (err) {
    Logger.log("Error saving thumbnail config sheet: " + err);
  }
}

function saveConfigSheet(keyName, keyValue) {
  try {
    if (!keyName || !keyValue) return;
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Config");
    if (!sheet) {
      sheet = ss.insertSheet("Config");
    }
    var data = sheet.getDataRange().getValues();
    if (data.length === 0 || (data.length === 1 && data[0][0] === "")) {
      sheet.clearContents();
      sheet.appendRow(["Key Name", "Key Value"]);
      sheet.appendRow([keyName, keyValue]);
      return;
    }

    var found = false;
    for (var i = 1; i < data.length; i++) {
      if (String(data[i][0] || "").trim().toUpperCase() === keyName.toUpperCase()) {
        sheet.getRange(i + 1, 2).setValue(keyValue);
        found = true;
        break;
      }
    }
    if (!found) {
      sheet.appendRow([keyName, keyValue]);
    }
  } catch (err) {
    Logger.log("Error saving config sheet: " + err);
  }
}

function savePastedData(category, rawText) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(category);
  if (!sheet) {
    sheet = ss.insertSheet(category);
  }
  sheet.clearContents();
  if (category === "OTT Updates") {
    sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date", "OTT Platform"]);
  } else if (category === "Release Updates") {
    sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date"]);
  } else {
    sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline"]);
  }

  var lines = rawText.trim().split("\n");
  for (var i = 0; i < lines.length; i++) {
    var cols = lines[i].split("\t");
    sheet.appendRow(cols);
  }
  return { status: "success", rows_added: lines.length };
}

function triggerGitHubAction(privacyStatus, driveUrl, userToken, sections) {
  var storedToken = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  var token = (userToken && userToken.trim()) ? userToken.trim() : storedToken;

  var url = "https://api.github.com/repos/YoutubeVideoUploader/auto-youtube-poster/actions/workflows/auto_youtube_poster.yml/dispatches";
  
  var payload = {
    "ref": "main",
    "inputs": {
      "privacy_status": privacyStatus || "unlisted",
      "drive_thumbnail_url": driveUrl || "",
      "sections": sections || "all"
    }
  };

  var options = {
    "method": "post",
    "contentType": "application/json",
    "headers": {
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github.v3+json"
    },
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };

  var response = UrlFetchApp.fetch(url, options);
  var code = response.getResponseCode();

  if (code === 200 || code === 204) {
    return { status: "success", code: code, message: "Successfully triggered 24/7 Cloud Render & Upload!" };
  } else {
    return { status: "error", code: code, message: response.getContentText() };
  }
}

function triggerGitHubActionHandler(privacyStatus, driveUrl, userToken, sections) {
  var res = triggerGitHubAction(privacyStatus, driveUrl, userToken, sections);
  return ContentService.createTextOutput(JSON.stringify(res))
    .setMimeType(ContentService.MimeType.JSON);
}

// Helper to set stored GITHUB_TOKEN property in Apps Script
function setGitHubTokenProperty(tokenString) {
  PropertiesService.getScriptProperties().setProperty("GITHUB_TOKEN", tokenString.trim());
  return "Successfully saved GITHUB_TOKEN property in Apps Script!";
}
