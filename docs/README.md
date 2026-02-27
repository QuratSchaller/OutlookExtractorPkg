# Outlook VTT Extractor v2.0

## What's New in v2.0

### Phase 1: Core Monitoring (CURRENT)
✅ **Automated Folder Monitoring**
- Monitor specific Outlook folder for new Webex recording emails
- Configurable polling (default: 1 hour)
- Filter by subject pattern: "Your Webex meeting content is available:"
- Persistent state management (JSON config file)

✅ **Approval Workflow**
- Pop-up dialog for each new email detected
- User approves or declines processing
- 60-second delay between processing emails (configurable)
- Tracks processed and ignored emails

✅ **Outlook Tasks Integration**
- Auto-creates tasks in Outlook from action items
- Tasks automatically sync to Microsoft To Do
- Default due date: 10 business days
- Categorized as "Webex Recording"

✅ **Webex Bot Integration**
- Sends action items to Webex bot (Producto) in Markdown format
- Includes meeting summary, action items, and user stories
- Link to recording included

✅ **Configuration Management**
- Settings saved to: `%APPDATA%\OutlookVTTExtractor\config_v2.json`
- Remembers monitored folder, processed emails, settings
- Clean separation from MVP version

### Phase 2: Advanced Integrations (PLANNED)
- Enhanced Microsoft To Do OAuth flow
- Jira auto-posting options
- Business days calculation improvements
- Due date parsing from transcript

### Phase 3: Background Running (PLANNED)
- System tray support
- Windows startup integration
- Settings panel UI
- Minimize to tray option

## File Structure

```
Outlook Items to Issues/
├── Outlook File Extractor              # MVP (v1.0) - stable version
├── Outlook File Extractor v2.0.py      # v2.0 with monitoring
├── meeting_classifier.py               # MVP classifier
├── meeting_classifier_v2.py            # v2.0 classifier (duplicate)
├── meeting_prompts.py                  # MVP prompts
├── meeting_prompts_v2.py              # v2.0 prompts (duplicate)
├── README_v2.md                        # This file
└── %APPDATA%\OutlookVTTExtractor\
    └── config_v2.json                  # Auto-generated config
```

## Configuration File Location

Settings are stored in:
```
C:\Users\<YourUsername>\AppData\Roaming\OutlookVTTExtractor\config_v2.json
```

### Config Structure:
```json
{
  "monitored_folder": "Inbox",
  "last_check_time": "2024-12-08T22:00:00",
  "processed_emails": ["entry_id_1", "entry_id_2"],
  "ignored_emails": ["entry_id_3"],
  "polling_interval_seconds": 3600,
  "processing_delay_seconds": 60,
  "email_subject_pattern": "Your Webex meeting content is available:",
  "monitoring_enabled": false,
  "output_directory": "C:\\Users\\...\\vtt_files"
}
```

## Environment Variables Required

Same as MVP, plus one new variable:

- `WEBEX_ACCESS_TOKEN` - Your Webex API token
- `WEBEX_BOT_TOKEN` - Producto bot token (NEW in v2.0)
- `CHATAI_CLIENT_ID` - Chat AI client ID
- `CHATAI_CLIENT_SECRET` - Chat AI client secret
- `CHATAI_APP_KEY` - Chat AI app key
- `JIRA_URL` - Your Jira instance URL
- `JIRA_EMAIL` - Your Jira email
- `JIRA_API_TOKEN` - Jira API token
- `JIRA_PROJECT_KEY` - Default project key

## How to Use

### Initial Setup
1. Set all required environment variables
2. Restart PowerShell/terminal
3. Run: `python "Outlook File Extractor v2.0.py"`
4. App auto-connects to Outlook on startup

### Start Monitoring
1. Specify folder name (e.g., "Inbox" or custom folder)
2. Click "Start Monitoring"
3. App polls every hour for new emails
4. Runs in foreground for now (Phase 3 will add tray support)

### When New Email Arrives
1. Pop-up dialog appears with meeting title
2. Click "Yes, Process" to analyze
3. Or click "No, Skip" to ignore
4. Wait 60 seconds before next email processed

### After Processing
- VTT file saved to output directory
- Analysis JSON + TXT files created
- Outlook Tasks auto-created (if enabled)
- Webex bot notified (if enabled)
- Analysis window shown for Jira review

## Testing the 60-Second Delay

For testing purposes, the delay between processing emails is set to 60 seconds.
To change to production 15 minutes:

1. Stop monitoring
2. Edit config file:
   - Change `"processing_delay_seconds": 60` to `900` (15 minutes)
3. Restart app and monitoring

## Comparison: MVP vs v2.0

| Feature | MVP (v1.0) | v2.0 |
|---------|-----------|------|
| Manual email selection | ✅ | ✅ |
| Automated monitoring | ❌ | ✅ |
| Approval dialogs | ❌ | ✅ |
| Outlook Tasks | ❌ | ✅ |
| Webex bot integration | ❌ | ✅ |
| Config persistence | ❌ | ✅ |
| System tray | ❌ | 🔄 Phase 3 |
| Windows startup | ❌ | 🔄 Phase 3 |

## Known Limitations (Phase 1)

- Must keep window open (no tray support yet)
- Manual start monitoring after launch
- Fixed polling interval (configurable in config file only)
- Webex bot sends to hardcoded email (needs configuration UI)
- No Windows startup integration yet

## Troubleshooting

### Monitoring Not Starting
- Ensure Outlook is connected (green status)
- Check folder name is correct
- Look for errors in Activity Log

### No Emails Detected
- Verify email subject contains: "Your Webex meeting content is available:"
- Check `last_check_time` in config - only emails after this time are processed
- Emails that arrived before monitoring started are ignored

### Tasks Not Creating
- Requires Outlook to be running and configured
- Check "Auto-create Outlook Tasks" is enabled
- Look for COM errors in log

### Webex Bot Not Working
- Verify `WEBEX_BOT_TOKEN` environment variable is set
- Check bot has permissions to send messages
- Email recipient is currently hardcoded - will be configurable in Phase 2

## Development Roadmap

### ✅ Completed
- Core monitoring loop
- Email filtering and approval
- Outlook Tasks integration
- Webex bot markdown messages
- Config persistence

### 🔄 In Progress (Phase 2)
- Microsoft To Do OAuth flow
- Configurable bot recipient
- Enhanced due date parsing
- Jira auto-posting workflow

### 📋 Planned (Phase 3)
- System tray icon and minimize
- Windows Task Scheduler integration
- Settings UI panel
- Notification improvements
- Background service mode

## Support

For issues or questions:
1. Check Activity Log for errors
2. Verify environment variables are set
3. Check config file in AppData folder
4. Compare with MVP version if issues persist
