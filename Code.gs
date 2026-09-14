// ==============================================================================
// Malayalam Movie News Studio - Google Apps Script (Code.gs)
// Handles Google Sheet Data Sync, Web App Interface, and 24/7 Cloud Action Triggers
// ==============================================================================

function doGet(e) {
  if (e && e.parameter && e.parameter.action === "get_data") {
    try {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var result = {};
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
        }
      }
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

    // 1. Handle GitHub Action Trigger Request from Web App / Website
    if (data.action === "trigger_github") {
      if (data.drive_thumbnail_url) {
        saveThumbnailConfigSheet(data.drive_thumbnail_url);
      }
      return triggerGitHubActionHandler(data.privacy_status, data.drive_thumbnail_url, data.token);
    }

    // 2. Handle Google Sheet Table Sync Request
    if (data.thumbnail_urls) {
      saveThumbnailConfigSheet(data.thumbnail_urls);
    }

    var tabName = data.tab_name;
    var rows = data.rows;

    if (tabName && rows) {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = ss.getSheetByName(tabName);
      if (!sheet) {
        sheet = ss.insertSheet(tabName);
      }

      // Clear old data and set headers (including Column D: Topic Headline)
      sheet.clearContents();
      sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline"]);

      // Write updated rows
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        sheet.appendRow([
          r["Topic Number"] || "",
          r["Malayalam News Text"] || "",
          r["Image URLs"] || "",
          r["Topic Headline"] || ""
        ]);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function saveThumbnailConfigSheet(urlsString) {
  try {
    if (!urlsString || typeof urlsString !== 'string') return;
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Thumbnail Config");
    if (!sheet) {
      sheet = ss.insertSheet("Thumbnail Config");
    }
    sheet.clearContents();
    sheet.appendRow(["Selected Image URLs"]);
    var urls = urlsString.split(/[\r\n,]+/);
    for (var i = 0; i < urls.length; i++) {
      var u = urls[i].trim();
      if (u) {
        sheet.appendRow([u]);
      }
    }
  } catch (err) {
    Logger.log("Error saving thumbnail config sheet: " + err);
  }
}

function savePastedData(category, rawText) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(category);
  if (!sheet) {
    sheet = ss.insertSheet(category);
  }
  sheet.clearContents();
  sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline"]);

  var lines = rawText.trim().split("\n");
  for (var i = 0; i < lines.length; i++) {
    var cols = lines[i].split("\t");
    sheet.appendRow(cols);
  }
  return { status: "success", rows_added: lines.length };
}

function triggerGitHubAction(privacyStatus, driveUrl, userToken) {
  var storedToken = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  var token = (userToken && userToken.trim()) ? userToken.trim() : storedToken;

  var url = "https://api.github.com/repos/YoutubeVideoUploader/auto-youtube-poster/actions/workflows/auto_youtube_poster.yml/dispatches";
  
  var payload = {
    "ref": "main",
    "inputs": {
      "privacy_status": privacyStatus || "unlisted",
      "drive_thumbnail_url": driveUrl || ""
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

function triggerGitHubActionHandler(privacyStatus, driveUrl, userToken) {
  var res = triggerGitHubAction(privacyStatus, driveUrl, userToken);
  return ContentService.createTextOutput(JSON.stringify(res))
    .setMimeType(ContentService.MimeType.JSON);
}

// Helper to set stored GITHUB_TOKEN property in Apps Script
function setGitHubTokenProperty(tokenString) {
  PropertiesService.getScriptProperties().setProperty("GITHUB_TOKEN", tokenString.trim());
  return "Successfully saved GITHUB_TOKEN property in Apps Script!";
}
