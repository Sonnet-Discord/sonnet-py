@echo off
REM This program initialises the development environment for Sonnet.

cls
title Sonnet DE Initialisation

echo Initialising Sonnet Development Environment...

echo. 
NET SESSION >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    ECHO User is an administrator. Proceeding...
) ELSE (
    ECHO You must run this as Administrator to proceed.
    PAUSE
    EXIT
)

echo. 
REM Initialise environment variables.
set /p LOC="Enter the location of your sonnet-py folder (e.g. C:\Users\Funey\sonnet-py): "
setx -m SONNET_LOCATION %LOC%

REM TODO: Maybe also add token here?

echo.
echo Initialisation complete.
pause
exit