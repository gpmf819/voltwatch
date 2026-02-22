# ─────────────────────────────────────────────────────────────────────────────
# Volt & Watt Market Watch — Morning Pre-fetch Script
# Runs at 7:00 AM via Windows Task Scheduler
# Fetches EV, Energy, and V2X news and saves to market-watch-cache.json
# alongside your market-watch.html file.
#
# SETUP:
#   1. Set your API key in the line below (ANTHROPIC_API_KEY)
#   2. Set the path to your market-watch.html folder (OUTPUT_DIR)
#   3. Follow the Task Scheduler instructions at the bottom of this file
# ─────────────────────────────────────────────────────────────────────────────

$ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY
$OUTPUT_DIR        = "$env:USERPROFILE\Desktop"   # Change to wherever your market-watch.html lives
$OUTPUT_FILE       = Join-Path $OUTPUT_DIR "market-watch-cache.json"
$LOG_FILE          = Join-Path $OUTPUT_DIR "market-watch-prefetch.log"

# ─── Logging ─────────────────────────────────────────────────────────────────

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line
}

Log "Starting Volt & Watt pre-fetch..."

# ─── Sector prompts ───────────────────────────────────────────────────────────

$sectors = @(
    @{
        key    = "ev"
        prompt = "Use web_search to find the 8 most recent, significant news articles from the last 48 hours about electric vehicles and automotive industry. Include EV launches, sales data, charging infrastructure, battery technology, automaker strategy, and EV policy. Return ONLY a raw JSON array (no markdown fences, no explanation). Each element must have: headline (exact article title), summary (1-2 sentence paraphrase in your own words), source (publication name), url (full direct article URL, not a homepage), time (e.g. '2h ago'), tags (array of 1-2 from ['EV','Market','Policy']), sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). Start with [ end with ]."
    },
    @{
        key    = "energy"
        prompt = "Use web_search to find the 8 most recent, significant news articles from the last 48 hours about residential energy, rooftop solar, home battery storage, net metering, solar incentives, and home electrification. Return ONLY a raw JSON array (no markdown fences, no explanation). Each element must have: headline (exact article title), summary (1-2 sentence paraphrase in your own words), source (publication name), url (full direct article URL, not a homepage), time (e.g. '3h ago'), tags (array of 1-2 from ['Energy','Market','Policy']), sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). Start with [ end with ]."
    },
    @{
        key    = "v2x"
        prompt = "Use web_search to find the 8 most recent, significant news articles from the last 48 hours about Vehicle-to-Everything (V2X) technology: V2G (vehicle-to-grid), V2H (vehicle-to-home), V2L (vehicle-to-load), bidirectional EV charging, and EV grid integration. Return ONLY a raw JSON array (no markdown fences, no explanation). Each element must have: headline (exact article title), summary (1-2 sentence paraphrase in your own words), source (publication name), url (full direct article URL, not a homepage), time (e.g. '4h ago'), tags (array of 1-2 from ['V2X','Market','Policy']), sentiment (one emoji: 📈 📉 ⚠️ ✅ ⚡ 🔬 📊 🛠️). Start with [ end with ]."
    }
)

# ─── Fetch function ───────────────────────────────────────────────────────────

function Fetch-Sector($sector) {
    Log "Fetching sector: $($sector.key)..."

    $body = @{
        model      = "claude-haiku-4-5-20251001"
        max_tokens = 4000
        tools      = @(@{ type = "web_search_20250305"; name = "web_search" })
        messages   = @(@{ role = "user"; content = $sector.prompt })
    } | ConvertTo-Json -Depth 10

    try {
        $response = Invoke-RestMethod `
            -Uri "https://api.anthropic.com/v1/messages" `
            -Method POST `
            -Headers @{
                "x-api-key"         = $ANTHROPIC_API_KEY
                "anthropic-version" = "2023-06-01"
                "Content-Type"      = "application/json"
            } `
            -Body $body

        # Extract text blocks
        $text = ($response.content | Where-Object { $_.type -eq "text" } | ForEach-Object { $_.text }) -join ""

        # Strip markdown fences
        $text = $text -replace '```json\s*', '' -replace '```', ''

        # Extract JSON array
        $start = $text.IndexOf('[')
        $end   = $text.LastIndexOf(']')

        if ($start -eq -1 -or $end -eq -1 -or $end -le $start) {
            Log "ERROR [$($sector.key)]: No JSON array found in response"
            return @()
        }

        $json  = $text.Substring($start, $end - $start + 1)
        $items = $json | ConvertFrom-Json

        # Filter valid items
        $valid = $items | Where-Object { $_.headline -and $_.url -and $_.url -ne '#' -and $_.url.StartsWith('http') }
        Log "OK [$($sector.key)]: $($valid.Count) articles fetched"
        return $valid

    } catch {
        Log "ERROR [$($sector.key)]: $_"
        return @()
    }
}

# ─── Run all sectors ──────────────────────────────────────────────────────────

$ev     = Fetch-Sector $sectors[0]
$energy = Fetch-Sector $sectors[1]
$v2x    = Fetch-Sector $sectors[2]

# ─── Write cache file ─────────────────────────────────────────────────────────

$cache = @{
    generatedAt = (Get-Date -Format "o")   # ISO 8601 timestamp
    ev          = $ev
    energy      = $energy
    v2x         = $v2x
} | ConvertTo-Json -Depth 10

$cache | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8
Log "Cache written to: $OUTPUT_FILE"
Log "Pre-fetch complete."

# ─────────────────────────────────────────────────────────────────────────────
# TASK SCHEDULER SETUP (run once to register the 7AM job)
#
# Open PowerShell as Administrator and run:
#
#   $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
#                -Argument "-NonInteractive -WindowStyle Hidden -File `"C:\Users\YourName\Desktop\prefetch.ps1`""
#   $trigger = New-ScheduledTaskTrigger -Daily -At "07:00AM"
#   $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
#   Register-ScheduledTask -TaskName "VoltWattPrefetch" `
#                          -Action $action -Trigger $trigger `
#                          -Settings $settings -RunLevel Highest
#
# To test it runs correctly right now:
#   powershell.exe -File "C:\Users\YourName\Desktop\prefetch.ps1"
#
# To check the log:
#   notepad "C:\Users\YourName\Desktop\market-watch-prefetch.log"
# ─────────────────────────────────────────────────────────────────────────────
