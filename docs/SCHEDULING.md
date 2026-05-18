# Local Scheduling

ai-signal-radio はローカル CLI とファイル保存だけで動くため、macOS なら `launchd`、Linux なら `cron` や systemd timer で日次実行できます。

## macOS launchd

`/Users/YOUR_NAME/Library/LaunchAgents/com.local.ai-signal-radio.plist` のようなファイルを作ります。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.local.ai-signal-radio</string>
  <key>WorkingDirectory</key>
  <string>/Users/YOUR_NAME/work/ai-signal-radio</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/uv</string>
    <string>run</string>
    <string>ai-signal</string>
    <string>run</string>
    <string>--config</string>
    <string>config/sources.yml</string>
    <string>--limit</string>
    <string>8</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/ai-signal-radio.out.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ai-signal-radio.err.log</string>
</dict>
</plist>
```

読み込み:

```bash
launchctl load ~/Library/LaunchAgents/com.local.ai-signal-radio.plist
```

## cron

```cron
0 8 * * * cd /path/to/ai-signal-radio && uv run ai-signal run --config config/sources.yml --limit 8 >> /tmp/ai-signal-radio.log 2>&1
```

VOICEVOX の音声生成も自動化する場合は、先に VOICEVOX engine が起動している必要があります。
