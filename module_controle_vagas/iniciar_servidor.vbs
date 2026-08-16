Set WshShell = CreateObject("WScript.Shell")

' 1. Captura a pasta atual onde o script esta sendo executado (Raiz do modulo)
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' 2. Executa o comando em modo oculto (0) e de forma assincrona (False)
WshShell.Run "py app.py", 0, False
