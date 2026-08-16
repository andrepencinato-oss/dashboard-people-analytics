Set WshShell = CreateObject("WScript.Shell")

' Obtém a pasta atual onde o script VBS está rodando (esperado estar junto do Absenteismo_plug.exe)
strScriptPath = Wscript.ScriptFullName
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFile = objFSO.GetFile(strScriptPath)
strFolder = objFSO.GetParentFolderName(objFile) 

WshShell.CurrentDirectory = strFolder

' Executa o servidor Flask (Absenteismo_plug.exe) silenciosamente em background (0 = invisivel)
WshShell.Run "Absenteismo_plug.exe", 0, False

' Aguarda 3 segundos para o servidor ligar
WScript.Sleep 3000

' Abre o navegador no IP local
WshShell.Run "http://localhost:5008"
