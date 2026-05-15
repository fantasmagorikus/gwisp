# Security Policy

## Supported Version

Gwisp is currently **Alpha build 1.0.3**.
This alpha build is currently tested on **Windows 11 only**.

## Windows Install Notes

- The default installer flow does not require administrator rights.
- The default installer flow does not create Desktop/Start Menu shortcuts, which
  avoids a common shortcut/COM false-positive path on Windows security tools.
- The project is not code-signed yet. Windows SmartScreen or unknown-publisher
  prompts can still appear for public downloads until a trusted code-signing
  certificate is used.

## Public-Use Warning

The developer of this project does not recommend using Gwisp in evaluated
certifications, real exams, paid graded activities, or any activity where
outside assistance is prohibited. Gwisp is a lab/test tool and must be treated
as such. The developer is not responsible for answer accuracy in evaluated,
graded, or paid activities. Use responsibly and at your own risk.

## Hinweis Zur Nutzung

Der Entwickler dieses Projekts empfiehlt nicht, Gwisp in bewerteten
Zertifizierungen, echten Pruefungen, bezahlten benoteten Aufgaben oder
Aktivitaeten zu nutzen, bei denen externe Hilfe verboten ist. Gwisp ist ein
Labor/Test-Tool und muss so behandelt werden. Der Entwickler uebernimmt keine
Verantwortung fuer die Genauigkeit der Antworten in bewerteten, benoteten oder
bezahlten Aktivitaeten. Nutzung auf eigene Verantwortung.

## Local Privacy Notes

- Keep `config.json`, `logs/`, `artifacts/`, `.env`, keys, certificates, and
  local validation media out of Git.
- Sync OCR is intended only for trusted local networks.
- Sync OCR sends screenshots over local HTTP protected by a random bearer token.
  Do not use it on untrusted networks.
- The main app sends OCR text to the selected AI provider. With `llm_provider`
  set to `ollama`, text stays on the configured Ollama endpoint. With
  `llm_provider` set to `cloud`, captured text is sent to the configured
  cloud API endpoint.
- Prefer `GWISP_CLOUD_API_KEY` for cloud credentials. If you add
  `cloud_api_key` to local `config.json`, keep that file out of Git.

## Reporting

Report security concerns privately to the project owner, @fantasmagorikus.
