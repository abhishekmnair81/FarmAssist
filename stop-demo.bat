@echo off
echo Stopping FarmAssist Demo safely...
echo.
docker compose stop
echo.
echo All containers have been safely stopped. 
echo Your OpenWA connection, session, and API key have been PRESERVED.
echo Run start-demo.bat tomorrow to resume instantly without rescanning QR.
echo.
pause
