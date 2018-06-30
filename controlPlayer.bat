@ECHO OFF
set arg1=%1

IF /i "%arg1%"=="mute" goto optionMute
IF /i "%arg1%"=="volUp" goto optionVolUp
IF /i "%arg1%"=="volDown" goto optionVolDown
IF /i "%arg1%"=="quit" goto optionQuit
exit

:optionMute
ECHO cycle mute >\\.\pipe\mpvyoutubeskt
exit

:optionVolUp
ECHO cycle volume +5 >\\.\pipe\mpvyoutubeskt
exit

:optionVolDown
ECHO cycle volume -5 >\\.\pipe\mpvyoutubeskt
exit

:optionQuit
echo quit >\\.\pipe\mpvyoutubeskt
exit