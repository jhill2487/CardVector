Set shell = CreateObject("WScript.Shell")
Set env = shell.Environment("PROCESS")

root = env("USERENVIRONMENT")
If root = "" Then
    root = env("USERPROFILE") & "\OneDrive\PutnamCollectibles"
End If

app = root & "\Platform\Putnam_OS\System\app\putnam_os.py"
cmd = "pyw.exe """ & app & """"

shell.Run cmd, 0, False
