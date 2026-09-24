' El truco sucio de VBScript que existe desde la época de Windows XP.
' Un archivo .bat siempre parpadea una ventana negra horrible en la pantalla.
' WScript.Shell.Run con parámetro 0 es la única forma que tiene Windows
' de levantar un proceso 100% invisible en segundo plano sin asustar al usuario.
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "pythonw.exe main.py", 0, False
