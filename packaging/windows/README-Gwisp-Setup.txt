Gwisp Setup
=====================
Alpha build 1.0.3
Copyright (c) 2026 Raphael (@fantasmagorikus). All rights reserved.

WINDOWS STATUS
Alpha build 1.0.3 is currently tested on Windows 11 only.
The default install flow does not require administrator rights and does not
create Desktop or Start Menu shortcuts. Open the Run-Gwisp-*.bat launchers from
the selected install folder.

The EXE is not code-signed yet. Windows SmartScreen or unknown-publisher prompts
can still appear for public downloads until a trusted code-signing certificate
is used.

WARNING
The developer of this project does not recommend using Gwisp in evaluated
certifications, real exams, paid graded activities, or activities where outside
assistance is prohibited. This is an alpha lab/test tool. Accuracy is not
guaranteed. Use responsibly and at your own risk.

HINWEIS
Der Entwickler empfiehlt nicht, Gwisp in bewerteten Zertifizierungen, echten
Pruefungen, bezahlten benoteten Aufgaben oder Aktivitaeten zu nutzen, bei denen
externe Hilfe verboten ist. Dies ist ein Alpha-Labor/Test-Tool. Genauigkeit ist
nicht garantiert. Nutzung auf eigene Verantwortung.

Run Gwisp-Setup.exe to open the graphical installer.

Language options:

- 🏴 English
- 🇧🇷 Portugues
- 🇩🇪 Deutsch

Support:

BTC: bc1qfnlslkc9lm7327d8ruz6us6rs25299fx752h4j
Monero: 46qeT3qhJgfYditXfaSqM1enNAottE26EQczmtNbiT57iJzFRHxuBjQN3jdtM8FPwFMRtQYWc9CSXBYLT7RhBaHcBfDvwrE

Install options:

- Os dois: installs the main Gwisp app and the Sync OCR companion.
- Somente app principal completo: installs only the main OCR app with support
  for local Ollama or a cloud AI API provider.
- Somente Sync OCR: installs only the secondary-machine capture companion.

Manual install option:

1. Download and extract Gwisp-Main-Windows.zip or Gwisp-SyncOCR-Windows.zip.
2. Run one of these commands from the extracted folder:

powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en
powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-SyncOCR.ps1 -Language en

Optional shortcuts:

powershell -ExecutionPolicy Bypass -File .\Install-Gwisp-Main.ps1 -Language en -CreateShortcuts

AI provider options for the main app:

- Local Ollama is the default. Install Ollama and download the configured model.
- Cloud API mode uses llm_provider=cloud, cloud_api_url, cloud_model, and
  GWISP_CLOUD_API_KEY. Do not commit real API keys.

The EXE first looks for the ZIP packages beside itself. If they are not there,
it downloads them from the latest GitHub release:

https://github.com/fantasmagorikus/gwisp/releases/latest/download

The URL must contain:

- Gwisp-Main-Windows.zip
- Gwisp-SyncOCR-Windows.zip
