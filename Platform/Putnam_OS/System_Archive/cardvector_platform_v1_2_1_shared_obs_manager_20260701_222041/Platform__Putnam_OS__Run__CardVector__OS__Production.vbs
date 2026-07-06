Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
platformDir = fso.GetParentFolderName(scriptDir)
root = fso.GetParentFolderName(platformDir)

app = root & "\Platform\Putnam_OS\System\app\putnam_os.py"
startupDir = root & "\Platform\Putnam_OS\System\logs\Startup Logs"
If Not fso.FolderExists(root & "\Platform\Putnam_OS\System\logs") Then
    fso.CreateFolder(root & "\Platform\Putnam_OS\System\logs")
End If
If Not fso.FolderExists(startupDir) Then
    fso.CreateFolder(startupDir)
End If

stamp = Replace(Replace(Replace(CStr(Now), "/", "-"), ":", "-"), " ", "_")
outFile = startupDir & "\production_launch_" & stamp & ".txt"
Set outStream = fso.OpenTextFile(outFile, 8, True)
outStream.WriteLine CStr(Now) & " | Launching CardVector OS v1.2.1 production"
outStream.Close

cmdFile = startupDir & "\run_cardvector_os_production.cmd"
Set cmdOut = fso.OpenTextFile(cmdFile, 2, True)
cmdOut.WriteLine "@echo off"
cmdOut.WriteLine "echo %date% %time% ^| Starting CardVector OS v1.2.1 >> """ & outFile & """"
cmdOut.WriteLine "py.exe """ & app & """ >> """ & outFile & """ 2>&1"
cmdOut.Close

shell.Run """" & cmdFile & """", 0, False
