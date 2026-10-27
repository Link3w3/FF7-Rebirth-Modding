@echo off
rem Packages the End project exactly like the editor's Package Project > Windows (64-bit), without the editor open.
rem Output goes to E:\FVIIREBIRTH\Pakage (same as the editor). Log: build\package.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\package.log"
echo Package started %DATE% %TIME%> "%LOG%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output >> "%LOG%" 2>&1
echo PACKAGE COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b
