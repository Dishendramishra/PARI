# ======================================================
#  Making sure that all modules are installed
# ======================================================
import pip

def install(package):
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])

modules = open("requirements","r").read().split()

for module in modules:
    install(module)
# ======================================================

import os, winshell, win32com.client

target = "main.pyw"
shortcut_name = 'PARI.lnk'

def create_shortcut(target=target, shortcut_name=shortcut_name):
    desktop = winshell.desktop()
    path = os.path.join(desktop, shortcut_name)
    cwd = os.getcwd()

    icon = os.path.abspath("resources")+"\\icons\\prl2.ico"
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = cwd+"\\"+target
    shortcut.WorkingDirectory = cwd
    shortcut.IconLocation = icon
    shortcut.save()

create_shortcut(target, shortcut_name)