@ECHO OFF

REM This script can be used under cygwin bash, which otherwise
REM the path passed to python may be /cygwin/c/... which the
REM Anaconda Python doesn't understand. 
REM Note: %~dp0 is the directory this script lives in.

python %~dp0\gcamtool.py %*
