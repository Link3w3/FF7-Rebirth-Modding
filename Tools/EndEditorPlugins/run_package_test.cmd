@echo off
rem Test of Package Project with the current plugins: same as run_package_project.cmd, but the packaged
rem build goes to C:\FF7R2UProj\Saved\PackageTest instead of E:\FVIIREBIRTH\Pakage. Log: build\package_test.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\package_test.log"
echo Package test started %DATE% %TIME%> "%LOG%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=C:/FF7R2UProj/Saved/PackageTest -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output >> "%LOG%" 2>&1
echo PACKAGE COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b
