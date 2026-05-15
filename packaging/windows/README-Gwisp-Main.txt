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
- One AI provider:
  - Local mode: Ollama installed on the main machine, with the configured model
    downloaded.
  - Cloud mode: llm_provider set to cloud, cloud_api_url/cloud_model configured,
    and GWISP_CLOUD_API_KEY set before running Gwisp, or a cloud_api_key value
    saved in local config.json by the installer.

Install
1. Extract this ZIP.
2. Open PowerShell in the extracted folder.
3. Run:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en
4. Open Run-Gwisp-Main.bat inside the install folder shown at the end.

Manual Cloud API example:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en -LlmProvider cloud -CloudApiUrl https://api.openai.com/v1/chat/completions -CloudModel gpt-4.1-mini

Optional shortcut install:
   powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en -CreateShortcuts

First run
1. Open Gwisp.
2. Confirm the AI provider line shows Local Ollama or Cloud API.
3. Click "Check setup".
4. Click "Load model".
5. Use "OCR box", "Select capture window", or "Sync OCR".
