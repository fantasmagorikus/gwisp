Gwisp Main - Windows installer ZIP
Alpha build 1.0.3
Copyright (c) 2026 Raphael (@fantasmagorikus). All rights reserved.

WARNING
The developer of this project does not recommend using Gwisp in evaluated
certifications, real exams, paid graded activities, or activities where outside
assistance is prohibited. This is an alpha lab/test tool. Accuracy is not
guaranteed. Use responsibly and at your own risk.

What this installs
- Main Gwisp desktop app.
- Local virtual environment under %LOCALAPPDATA%\Gwisp\Main.
- Launcher file named Run-Gwisp-Main.bat inside the install folder.
- No shortcuts are created by default. Optional shortcuts can be created with
  -CreateShortcuts.

Requirements
- Windows 11. Alpha build 1.0.3 is currently tested only on Windows 11.
- Python 3.11 or newer.
- Internet access during install to download Python packages.
- Tesseract OCR installed on the main machine.
- Ollama installed on the main machine, with the configured model downloaded.

Install
1. Extract this ZIP.
2. Open PowerShell in the extracted folder.
3. Run:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en
4. Open Run-Gwisp-Main.bat inside the install folder shown at the end.

Optional shortcut install:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en -CreateShortcuts

First run
1. Open Gwisp.
2. Click "Check setup".
3. Click "Load model".
4. Use "OCR box", "Select capture window", or "Sync OCR".
