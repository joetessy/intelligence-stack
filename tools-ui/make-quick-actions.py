#!/usr/bin/env python3
"""
make-quick-actions.py — install two Finder Quick Actions (macOS Services):

  * "OCR to text"                — right-click a file -> OCR to <name>.ocr.txt
  * "Sheet music to MuseScore"   — right-click a file -> .mscz in omr-out/

They wrap the same CLIs the webapp uses (bin/ocr and musescore/omr/sheet2mscz),
so nothing new is duplicated. Run once:  python3 make-quick-actions.py
If they don't appear: System Settings > Keyboard/Login Items & Extensions >
Quick Actions (or Finder right-click > Quick Actions > Customize).
"""
import plistlib
import subprocess
import uuid
from pathlib import Path

SERVICES = Path.home() / "Library" / "Services"

OCR_SCRIPT = r'''for f in "$@"; do
  out="${f%.*}.ocr.txt"
  "$HOME/Projects/intelligence-stack/bin/ocr" "$f" --task text > "$out" 2>/dev/null && open -R "$out"
done
osascript -e 'display notification "OCR complete" with title "OCR to text"' >/dev/null 2>&1
'''

SCORE_SCRIPT = r'''d=""
for f in "$@"; do
  "$HOME/Projects/musescore/omr/sheet2mscz" "$f" >/dev/null 2>&1
  d="$(dirname "$f")/omr-out"
done
[ -n "$d" ] && [ -d "$d" ] && open "$d"
osascript -e 'display notification "Score converted to omr-out/" with title "Sheet music to MuseScore"' >/dev/null 2>&1
'''


def wflow(script: str) -> dict:
    return {
        "AMApplicationBuild": "521",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [{
            "action": {
                "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
                "AMActionVersion": "2.0.3",
                "AMApplication": ["Automator"],
                "AMParameterProperties": {k: {} for k in
                                          ("COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell", "source")},
                "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
                "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
                "ActionName": "Run Shell Script",
                "ActionParameters": {
                    "COMMAND_STRING": script,
                    "CheckedForUserDefaultShell": True,
                    "inputMethod": 1,  # pass selected files as "$@"
                    "shell": "/bin/bash",
                    "source": "",
                },
                "BundleIdentifier": "com.apple.Automator.RunShellScript",
                "CFBundleVersion": "2.0.3",
                "CanShowSelectedItemsWhenRun": False,
                "CanShowWhenRun": True,
                "Category": ["AMCategoryUtilities"],
                "Class Name": "RunShellScriptAction",
                "InputUUID": str(uuid.uuid4()).upper(),
                "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
                "OutputUUID": str(uuid.uuid4()).upper(),
                "UUID": str(uuid.uuid4()).upper(),
                "UnlocalizedApplications": ["Automator"],
                "arguments": {
                    "0": {"default value": 0, "name": "inputMethod", "required": "0", "type": "0", "uuid": "0"},
                    "1": {"default value": False, "name": "CheckedForUserDefaultShell", "required": "0", "type": "0", "uuid": "1"},
                    "2": {"default value": "", "name": "source", "required": "0", "type": "0", "uuid": "2"},
                    "3": {"default value": "/bin/sh", "name": "shell", "required": "0", "type": "0", "uuid": "3"},
                    "4": {"default value": "", "name": "COMMAND_STRING", "required": "0", "type": "0", "uuid": "4"},
                },
                "isViewVisible": 1,
                "location": "309.000000:253.000000",
                "nibPath": "/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib",
            },
            "isViewVisible": 1,
        }],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleIDsByProvider": {},
            "applicationPaths": [],
            "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 0,
            "processesInput": 0,
            "serviceApplicationBundleID": "com.apple.finder",
            "serviceApplicationName": "Finder",
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def info(menu_name: str) -> dict:
    return {"NSServices": [{
        "NSMenuItem": {"default": menu_name},
        "NSMessage": "runWorkflowAsService",
        "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
        "NSSendFileTypes": ["public.item"],
    }]}


def install(name: str, script: str) -> None:
    d = SERVICES / f"{name}.workflow" / "Contents"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "Info.plist", "wb") as f:
        plistlib.dump(info(name), f)
    with open(d / "document.wflow", "wb") as f:
        plistlib.dump(wflow(script), f)
    print(f"installed: {d.parent}")


if __name__ == "__main__":
    SERVICES.mkdir(parents=True, exist_ok=True)
    install("OCR to text", OCR_SCRIPT)
    install("Sheet music to MuseScore", SCORE_SCRIPT)
    subprocess.run(["/System/Library/CoreServices/pbs", "-flush"], check=False)
    print("done. If not shown: System Settings > Login Items & Extensions > Quick Actions.")
