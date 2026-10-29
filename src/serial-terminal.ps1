param(
    [ValidatePattern('^COM[0-9]+$')][string]$PortName = '',
    [ValidateRange(300, 3000000)][int]$BaudRate = 115200,
    [switch]$UniqueLog,
    [switch]$EnableTx,
    [string]$SeedLogPath = '',
    [string]$Command = '',
    [switch]$ClearInputLine,
    [ValidateRange(1, 600)][int]$ReadSeconds = 4,
    [switch]$StopAutoboot,
    [ValidateSet('Enter', 'ControlC')][string]$AutobootKey = 'Enter',
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'

function Get-UartLineKey([string]$Line) {
    return ($Line -replace '\[\s*[0-9]+\.[0-9]+(?:@\s*[0-9]+)?\]\s*', '').TrimEnd("`r")
}

function Test-UartBootloaderPrompt([string]$Text) {
    return [bool]($Text -match '(?m)(?:^|[\r\n])(?:=>|[A-Za-z0-9_.-]{1,40}[#>])[ ]*$')
}

function ConvertTo-UartInput([ConsoleKeyInfo]$KeyInfo) {
    if ($KeyInfo.Key -eq [ConsoleKey]::Enter) { return "`r" }
    if ($KeyInfo.Key -eq [ConsoleKey]::Backspace) { return [string][char]127 }
    if ($KeyInfo.KeyChar -ne [char]0) { return [string]$KeyInfo.KeyChar }
    return ''
}

if ($SelfTest) {
    $enterKey = New-Object ConsoleKeyInfo ([char]13), ([ConsoleKey]::Enter), $false, $false, $false
    $letterKey = New-Object ConsoleKeyInfo ([char]'a'), ([ConsoleKey]::A), $false, $false, $false
    $functionKey = New-Object ConsoleKeyInfo ([char]0), ([ConsoleKey]::F2), $false, $false, $false
    if ((ConvertTo-UartInput $enterKey) -cne "`r") { throw 'Enter mapping failed' }
    if ((ConvertTo-UartInput $letterKey) -cne 'a') { throw 'Character mapping failed' }
    if ((ConvertTo-UartInput $functionKey) -cne '') { throw 'Function key mapping failed' }
    $testCharacters = [char[]]'UART RX'
    if ([string]::new($testCharacters, 0, 7) -cne 'UART RX') { throw 'RX text decoding failed' }
    if ((Get-UartLineKey '[ 1.123456@0] reboot') -cne (Get-UartLineKey '[ 9.654321@3] reboot')) { throw 'Dedup timestamp normalization failed' }
    if ((Get-UartLineKey 'error 21') -ceq (Get-UartLineKey 'error 22')) { throw 'Dedup removed distinct errors' }
    if (-not (Test-UartBootloaderPrompt "boot log`r`ng12a_u212_v1# ")) { throw 'Bootloader prompt not detected' }
    if (Test-UartBootloaderPrompt "Linux log`r`n# ") { throw 'Android shell mistaken for bootloader' }
    'PASS: key mapping, RX text construction and dedup; no serial port opened, no device writes.'
    return
}

if (-not $PortName) { throw 'Pass -PortName with the COM port detected on this PC.' }

$sessionName = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$sessionDirectory = Join-Path $PSScriptRoot $sessionName
[void][IO.Directory]::CreateDirectory($sessionDirectory)
$statusPath = Join-Path $PSScriptRoot 'status.json'
$serialPort = New-Object IO.Ports.SerialPort $PortName, $BaudRate, ([IO.Ports.Parity]::None), 8, ([IO.Ports.StopBits]::One)
$serialPort.Handshake = [IO.Ports.Handshake]::None
$serialPort.DtrEnable = $false
$serialPort.RtsEnable = $false
$serialPort.ReadTimeout = 200
$serialPort.WriteTimeout = 200
$txEnabled = [bool]$EnableTx
$rxBytes = 0L
$txBytes = 0L
$rxLog = $null
$textLog = $null
$uniqueLogPath = Join-Path $PSScriptRoot 'rx-unique.txt'
$seenLines = [Collections.Generic.HashSet[string]]::new()
$pendingLine = ''
$uniqueLines = 0L
$duplicatesSkipped = 0L
$failure = $null
$utf8 = New-Object Text.UTF8Encoding $false
$decoder = $utf8.GetDecoder()
$readBuffer = New-Object byte[] 4096
$characterBuffer = New-Object char[] 8192
$bootWatchText = ''
$bootWatchStarted = $false
$bootInterruptDeadline = [DateTime]::MinValue
$bootInterruptLastSend = [DateTime]::MinValue
$bootloaderPromptSeen = $false
$commandResponse = ''
$commandPromptReturned = $false

function Save-Status([string]$State) {
    $status = [ordered]@{ state=$State; pid=$PID; port=$PortName; baud=$BaudRate;
        format='8N1'; handshake='None'; dtr=$false; rts=$false; txEnabled=$txEnabled;
        rxBytes=$rxBytes; txBytes=$txBytes; updatedUtc=[DateTime]::UtcNow.ToString('o');
        sessionDirectory=$sessionDirectory; uniqueLog=[bool]$UniqueLog; uniqueLogPath=$uniqueLogPath;
        uniqueLines=$uniqueLines; duplicatesSkipped=$duplicatesSkipped;
        stopAutoboot=[bool]$StopAutoboot; autobootKey=$AutobootKey;
        bootloaderPromptSeen=$bootloaderPromptSeen; error=$failure }
    [IO.File]::WriteAllText($statusPath, ($status | ConvertTo-Json), $utf8)
}

try {
    if ($EnableTx -and ($Command -or $StopAutoboot)) { throw 'EnableTx is for interactive sessions only.' }
    if ($Command -and $StopAutoboot) { throw 'Choose either a one-shot command or an autoboot interruption.' }
    if ($ClearInputLine -and -not $Command) { throw 'ClearInputLine requires an explicitly selected command.' }
    if ($UniqueLog) {
        foreach ($seed in @($SeedLogPath, $uniqueLogPath)) {
            if ($seed -and (Test-Path -LiteralPath $seed)) {
                foreach ($line in ([IO.File]::ReadAllText($seed, $utf8) -split "`n")) {
                    [void]$seenLines.Add((Get-UartLineKey $line))
                }
            }
        }
        $textStream = [IO.File]::Open($uniqueLogPath, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
        $textLog = [IO.StreamWriter]::new($textStream, $utf8)
    } else {
        $rxLog = New-Object IO.FileStream (Join-Path $sessionDirectory 'rx.bin'), ([IO.FileMode]::CreateNew), ([IO.FileAccess]::Write), ([IO.FileShare]::ReadWrite)
        $textLog = New-Object IO.StreamWriter (Join-Path $sessionDirectory 'rx.txt'), $false, $utf8
    }
    $textLog.AutoFlush = $true
    if (-not $Command) { [Console]::TreatControlCAsInput = $true }
    $serialPort.Open()
    $initialMode = if ($txEnabled) { 'TX ARMED' } else { 'RX ONLY' }
    [Console]::Title = "BFX-AT100 UART $PortName $BaudRate - $initialMode"
    [Console]::WriteLine("OPEN: $PortName, $BaudRate baud, 8N1, no flow control, DTR/RTS off.")
    if ($Command) {
        [Console]::WriteLine('EXPLICIT COMMAND: send the selected line once; interactive TX stays disabled.')
    } else {
        if ($StopAutoboot) {
            [Console]::WriteLine("AUTOBOOT WATCH: after the next U-Boot banner, send $AutobootKey for up to 12 seconds; stop on a bootloader prompt.")
        } else { [Console]::WriteLine("${initialMode}: no startup bytes or boot-interrupt keys are sent.") }
        [Console]::WriteLine('F2: manually arm/disarm TX. F10: stop and release the port.')
    }
    [Console]::WriteLine("RX logs: $(if ($UniqueLog) { $uniqueLogPath } else { $sessionDirectory })")
    Save-Status 'open'
    $commandTimer = [Diagnostics.Stopwatch]::StartNew()
    if ($Command) {
        if ($Command.Contains("`r") -or $Command.Contains("`n")) { throw 'Command must be a single explicitly selected line.' }
        Start-Sleep -Milliseconds 200
        if ($ClearInputLine) {
            # CH343 port-open transients can leave a garbage command prefix.
            $serialPort.Write([string][char]21)
            $txBytes++
            Start-Sleep -Milliseconds 50
        }
        $commandBytes = $utf8.GetBytes($Command + "`r")
        $serialPort.Write($commandBytes, 0, $commandBytes.Length)
        $txBytes += $commandBytes.Length
        [Console]::WriteLine('[Explicit one-shot diagnostic command sent; interactive TX remains disabled.]')
        Save-Status 'open'
    }
    $statusTimer = [Diagnostics.Stopwatch]::StartNew()
    while ($serialPort.IsOpen) {
        $available = $serialPort.BytesToRead
        if ($available -gt 0) {
            $count = $serialPort.Read($readBuffer, 0, [Math]::Min($available, $readBuffer.Length))
            if ($null -ne $rxLog) {
                $rxLog.Write($readBuffer, 0, $count)
                $rxLog.Flush()
            }
            $rxBytes += $count
            $characterCount = $decoder.GetChars($readBuffer, 0, $count, $characterBuffer, 0, $false)
            $text = [string]::new($characterBuffer, 0, $characterCount)
            if ($Command) {
                $commandResponse += $text
                if ($commandResponse.Length -gt 4096) { $commandResponse = $commandResponse.Substring($commandResponse.Length - 4096) }
                $commandPromptReturned = Test-UartBootloaderPrompt $commandResponse
            }
            if ($StopAutoboot) {
                $bootWatchText += $text
                if ($bootWatchText.Length -gt 4096) { $bootWatchText = $bootWatchText.Substring($bootWatchText.Length - 4096) }
                if (-not $bootWatchStarted -and $bootWatchText -match 'U-Boot 2015\.') {
                    $bootWatchStarted = $true
                    $bootInterruptDeadline = [DateTime]::UtcNow.AddSeconds(12)
                }
                if ($bootWatchStarted -and (Test-UartBootloaderPrompt $bootWatchText)) {
                    $bootloaderPromptSeen = $true
                    $bootInterruptDeadline = [DateTime]::MinValue
                }
                if ($bootWatchText -match 'Starting kernel') { $bootInterruptDeadline = [DateTime]::MinValue }
                if ($bootWatchText -match '(?i)password:') { $bootInterruptDeadline = [DateTime]::MinValue }
            }
            if ($UniqueLog) {
                $pendingLine += $text
                $lines = $pendingLine -split "`n"
                $pendingLine = $lines[-1]
                for ($lineIndex = 0; $lineIndex -lt ($lines.Length - 1); $lineIndex++) {
                    $lineKey = Get-UartLineKey $lines[$lineIndex]
                    if ($lineKey.Length -gt 0 -and $seenLines.Add($lineKey)) {
                        $textLog.WriteLine($lines[$lineIndex].TrimEnd("`r"))
                        $uniqueLines++
                    } else { $duplicatesSkipped++ }
                }
            } else { $textLog.Write($text) }
            # Render terminal control bytes visibly; preserve original bytes in rx.bin.
            [Console]::Write(($text -replace '[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '?'))
            Save-Status 'open'
        }
        if ($StopAutoboot -and [DateTime]::UtcNow -lt $bootInterruptDeadline -and
            ([DateTime]::UtcNow - $bootInterruptLastSend).TotalMilliseconds -ge 150) {
            $interruptText = if ($AutobootKey -eq 'ControlC') { [string][char]3 + "`r" } else { "`r" }
            $serialPort.Write($interruptText)
            $txBytes += $interruptText.Length
            $bootInterruptLastSend = [DateTime]::UtcNow
        }
        if ($Command -and ($commandPromptReturned -or $commandTimer.Elapsed.TotalSeconds -ge $ReadSeconds)) { break }
        if ($statusTimer.ElapsedMilliseconds -ge 1000) {
            Save-Status 'open'
            $statusTimer.Restart()
        }
        if (-not $Command -and [Console]::KeyAvailable) {
            $keyInfo = [Console]::ReadKey($true)
            if ($keyInfo.Key -eq [ConsoleKey]::F10) { break }
            if ($keyInfo.Key -eq [ConsoleKey]::F2) {
                $txEnabled = -not $txEnabled
                $mode = if ($txEnabled) { 'TX ARMED' } else { 'RX ONLY' }
                [Console]::Title = "BFX-AT100 UART $PortName $BaudRate - $mode"
                [Console]::WriteLine("`r`n[$mode]")
                Save-Status 'open'
            } elseif ($txEnabled) {
                $keyText = ConvertTo-UartInput $keyInfo
                if ($keyText.Length -gt 0) {
                    $keyBytes = $utf8.GetBytes($keyText)
                    $serialPort.Write($keyBytes, 0, $keyBytes.Length)
                    $txBytes += $keyBytes.Length
                    Save-Status 'open'
                }
            }
        }
        Start-Sleep -Milliseconds 10
    }
} catch {
    $failure = $_.Exception.Message
    [Console]::WriteLine("`r`nERROR: $failure")
} finally {
    if ($serialPort.IsOpen) { $serialPort.Close() }
    $serialPort.Dispose()
    if ($null -ne $rxLog) { $rxLog.Dispose() }
    if ($null -ne $textLog) {
        if ($UniqueLog -and $pendingLine.Length -gt 0 -and $seenLines.Add((Get-UartLineKey $pendingLine))) { $textLog.WriteLine($pendingLine) }
        $textLog.Dispose()
    }
    Save-Status $(if ($failure) { 'error' } else { 'closed' })
    [Console]::WriteLine("`r`nCLOSED. RX=$rxBytes bytes, TX=$txBytes bytes. Logs: $sessionDirectory")
}
