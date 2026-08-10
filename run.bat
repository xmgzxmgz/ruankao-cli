@echo off
title devkit
cd /d "%~dp0"
"%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" drill.py %*
