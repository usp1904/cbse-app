# PowerShell script to register CBSE App as a Windows Startup Task
# Run this script as Administrator to register the task.

param (
    [string]$Mode = "server" # Options: "server" or "mesh"
)

# Ensure administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this PowerShell script as Administrator!"
    Exit
}

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Get-Location
}

# Resolve WSL path to Windows path if running via WSL mapping
if ($ScriptDir.StartsWith("\\wsl$")) {
    # Extract WSL path and convert or warn
    Write-Warning "Running from a WSL network path ($ScriptDir)."
    Write-Warning "Ensure Windows has access to this network share on boot, or copy the files to a local NTFS drive."
}

$ActionScript = Join-Path $ScriptDir "start_background.bat"
$TaskName = "CBSEAppAutoStart"

# Action to run start_background.bat
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ActionScript`" $Mode"

# Trigger: At startup
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Settings: Allow run on battery, do not stop on idle, restart if failed
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)

# Principal: Run as current user with elevated privileges
$User = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "Registering task '$TaskName' to run at system startup..."
Write-Host "Action: cmd.exe /c `"$ActionScript`" $Mode"
Write-Host "User:   $User"

# Remove existing task if it exists
if (Get-ScheduledTask -TaskPath "\" -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User $User -RunLevel Highest

Write-Host ""
Write-Host "=== Registration Successful! ==="
Write-Host "The application is now registered to start automatically in the background on boot."
Write-Host "You can manage this task in 'Task Scheduler' under the name '$TaskName'."
Write-Host "To start it immediately, run: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To stop it, run: Stop-ScheduledTask -TaskName '$TaskName'"
