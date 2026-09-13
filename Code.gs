// ==============================================================================
// Malayalam Movie News Studio - Google Apps Script (Code.gs)
// Handles Google Sheet Data Sync, Web App Interface, and 24/7 Cloud Action Triggers
// ==============================================================================

function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('dashboard_apps_script')
    .setTitle('Malayalam Movie News Studio')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // 1. Handle GitHub Action Trigger Request
    if (data.action === "trigger_github") {
      return triggerGitHubActionHandler(data.privacy_status, data.drive_thumbnail_url, data.token);
    }

    // 2. Handle Google Sheet Table Sync Request
    var tabName = data.tab_name;
    var rows = data.rows;

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(tabName);
    if (!sheet) {
      sheet = ss.insertSheet(tabName);
    }

    // Clear old data and set headers
    sheet.clearContents();
    sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs"]);

    // Write updated rows
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      sheet.appendRow([r["Topic Number"], r["Malayalam News Text"], r["Image URLs"]]);
    }

    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function savePastedData(category, rawText) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(category);
  if (!sheet) {
    sheet = ss.insertSheet(category);
  }
  sheet.clearContents();
  sheet.appendRow(["Topic Number", "Malayalam News Text", "Image URLs"]);

  var lines = rawText.trim().split("\n");
  for (var i = 0; i < lines.length; i++) {
    var cols = lines[i].split("\t");
    sheet.appendRow(cols);
  }
  return { status: "success", rows_added: lines.length };
}

function triggerGitHubAction(privacyStatus, driveUrl, userToken) {
  var token = userToken;
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
