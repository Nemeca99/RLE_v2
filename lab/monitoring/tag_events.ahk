; F9 = Teamfight, F10 = Objective, F11 = Death
F9::FileAppend, %A_NowUTC%`,event`,teamfight`n, %A_ScriptDir%\logs\rle_events.csv
F10::FileAppend, %A_NowUTC%`,event`,objective`n, %A_ScriptDir%\logs\rle_events.csv
F11::FileAppend, %A_NowUTC%`,event`,death`n, %A_ScriptDir%\logs\rle_events.csv

