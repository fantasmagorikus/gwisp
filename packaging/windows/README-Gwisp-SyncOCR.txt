Gwisp Sync OCR - Windows installer ZIP
Alpha build 1.0.3
Copyright (c) 2026 Raphael (@fantasmagorikus). All rights reserved.

WARNING
The developer of this project does not recommend using Gwisp in evaluated
certifications, real exams, paid graded activities, or activities where outside
assistance is prohibited. This is an alpha lab/test tool. Accuracy is not
guaranteed. Use responsibly and at your own risk.

What this installs
- Secondary-machine Sync OCR companion app.
- Local virtual environment under %LOCALAPPDATA%\Gwisp\SyncOCR.
- Launcher file named Run-Gwisp-SyncOCR.bat inside the install folder.
- No shortcuts are created by default. Optional shortcuts can be created with
  -CreateShortcuts.

Requirements
- Windows 11. Alpha build 1.0.3 is currently tested only on Windows 11.
- Python 3.11 or newer.
- Internet access during install to download Python packages.
- Both machines must be on the same trusted local network.

Install
1. Extract this ZIP on the secondary machine.
2. Open PowerShell in the extracted folder.
3. Run:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-SyncOCR.ps1 -Language en
4. Open Run-Gwisp-SyncOCR.bat inside the install folder shown at the end.

Optional shortcut install:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-SyncOCR.ps1 -Language en -CreateShortcuts

Sync flow
1. On the secondary machine, open Gwisp Sync OCR.
2. Click "Sync OCR".
3. Copy the Host, Port, and Token shown in the window.
4. On the main machine, open Gwisp, click "Sync OCR", paste those details, and connect.
