@echo off
REM This program prepares Sonnet for a push to GitHub or another Source Control system.

cls
title Sonnet Push Preparation
echo Preparing Sonnet for pushing...

REM Enter Sonnet Working Directory
echo   -  Entering Sonnet Working Directory.

REM Clear errors.
echo   -  Clearing out error logs.
del %SONNET_LOCATION%\err.log >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo      -  OK
) ELSE (
    echo      -  Failed or does not exist.
)


REM Done.
echo Preparation complete.
pause
exit
