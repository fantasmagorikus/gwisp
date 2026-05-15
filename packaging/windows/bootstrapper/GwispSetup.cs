using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace GwispSetup
{
    internal enum InstallChoice
    {
        Both,
        Main,
        SyncOcr
    }

    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            if (args.Length == 1 && string.Equals(args[0], "--self-test", StringComparison.OrdinalIgnoreCase))
            {
                return Uri.IsWellFormedUriString(InstallerForm.DefaultReleaseBaseUrl, UriKind.Absolute) ? 0 : 2;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
            return 0;
        }
    }

    internal sealed partial class InstallerForm : Form
    {
        public const string DefaultReleaseBaseUrl =
            "https://github.com/fantasmagorikus/gwisp/releases/latest/download";

        private const string MainZipName = "Gwisp-Main-Windows.zip";
        private const string SyncZipName = "Gwisp-SyncOCR-Windows.zip";
        private const string VersionLabel = "Alpha build 1.0.3";
        private const string SignatureText = "Alpha build 1.0.3 | > developed by @fantasmagorikus";

        private static readonly Color XpControl = Color.FromArgb(236, 233, 216);
        private static readonly Color XpControlDark = Color.FromArgb(172, 168, 153);
        private static readonly Color XpInfo = Color.FromArgb(255, 255, 225);
        private static readonly Color XpWindow = Color.White;
        private static readonly Color XpText = Color.Black;
        private static readonly Color XpStatusBlue = Color.FromArgb(10, 36, 106);

        private readonly Icon appIcon;
        private readonly Label titleLabel;
        private readonly Label introLabel;
        private readonly Label languageLabel;
        private readonly ComboBox languageSelector;
        private readonly Label noticeLabel;
        private readonly GroupBox choiceGroup;
        private readonly RadioButton installBoth;
        private readonly RadioButton installMain;
        private readonly RadioButton installSync;
        private readonly GroupBox providerGroup;
        private readonly RadioButton providerOllama;
        private readonly RadioButton providerCloud;
        private readonly Label cloudUrlLabel;
        private readonly TextBox cloudUrlText;
        private readonly Label cloudModelLabel;
        private readonly TextBox cloudModelText;
        private readonly Label cloudKeyLabel;
        private readonly TextBox cloudKeyText;
        private readonly Label cloudKeyNotice;
        private readonly GroupBox destinationGroup;
        private readonly TextBox installRoot;
        private readonly Button browseButton;
        private readonly GroupBox progressGroup;
        private readonly Button installButton;
        private readonly ProgressBar progressBar;
        private readonly TextBox logBox;
        private readonly Label statusLabel;
        private string currentLanguage = "pt";

        public InstallerForm()
        {
            appIcon = LoadSetupIcon();

            Text = Translate("windowTitle");
            Icon = appIcon;
            ShowIcon = true;
            Width = 690;
            Height = 760;
            Font = new Font("Tahoma", 8F, FontStyle.Regular);
            BackColor = XpControl;
            ForeColor = XpText;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;

            Panel headerFrame = CreateRaisedPanel(22, 16, 626, 76);
            Controls.Add(headerFrame);

            PictureBox iconBox = new PictureBox();
            iconBox.Left = 12;
            iconBox.Top = 14;
            iconBox.Width = 40;
            iconBox.Height = 40;
            iconBox.SizeMode = PictureBoxSizeMode.CenterImage;
            iconBox.Image = appIcon.ToBitmap();
            headerFrame.Controls.Add(iconBox);

            titleLabel = new Label();
            titleLabel.Left = 62;
            titleLabel.Top = 12;
            titleLabel.Width = 350;
            titleLabel.Height = 22;
            titleLabel.Font = new Font("Tahoma", 10F, FontStyle.Bold);
            titleLabel.BackColor = XpControl;
            headerFrame.Controls.Add(titleLabel);

            introLabel = new Label();
            introLabel.Left = 62;
            introLabel.Top = 38;
            introLabel.Width = 350;
            introLabel.Height = 28;
            introLabel.BackColor = XpControl;
            headerFrame.Controls.Add(introLabel);

            languageLabel = new Label();
            languageLabel.Left = 438;
            languageLabel.Top = 12;
            languageLabel.Width = 160;
            languageLabel.Height = 16;
            languageLabel.BackColor = XpControl;
            headerFrame.Controls.Add(languageLabel);

            languageSelector = new ComboBox();
            languageSelector.Left = 438;
            languageSelector.Top = 34;
            languageSelector.Width = 160;
            languageSelector.Height = 22;
            languageSelector.DropDownStyle = ComboBoxStyle.DropDownList;
            languageSelector.Items.Add("\uD83C\uDFF4 English");
            languageSelector.Items.Add("\uD83C\uDDE7\uD83C\uDDF7 Portugues");
            languageSelector.Items.Add("\uD83C\uDDE9\uD83C\uDDEA Deutsch");
            languageSelector.SelectedIndex = 1;
            languageSelector.SelectedIndexChanged += LanguageSelectorChanged;
            headerFrame.Controls.Add(languageSelector);

            noticeLabel = CreateInfoLabel("");
            noticeLabel.Left = 22;
            noticeLabel.Top = 104;
            noticeLabel.Width = 626;
            noticeLabel.Height = 34;
            Controls.Add(noticeLabel);

            choiceGroup = CreateGroupBox("", 22, 150, 626, 126);
            Controls.Add(choiceGroup);

            installBoth = CreateRadioButton("", 18, 26, true);
            installBoth.CheckedChanged += InstallChoiceChanged;
            choiceGroup.Controls.Add(installBoth);

            installMain = CreateRadioButton("", 18, 56, false);
            installMain.CheckedChanged += InstallChoiceChanged;
            choiceGroup.Controls.Add(installMain);

            installSync = CreateRadioButton("", 18, 86, false);
            installSync.CheckedChanged += InstallChoiceChanged;
            choiceGroup.Controls.Add(installSync);

            providerGroup = CreateGroupBox("", 22, 288, 626, 134);
            Controls.Add(providerGroup);

            providerOllama = CreateRadioButton("", 18, 24, true);
            providerOllama.CheckedChanged += ProviderChanged;
            providerGroup.Controls.Add(providerOllama);

            providerCloud = CreateRadioButton("", 18, 52, false);
            providerCloud.CheckedChanged += ProviderChanged;
            providerGroup.Controls.Add(providerCloud);

            cloudUrlLabel = CreatePlainLabel("", 36, 82, 82, 18);
            providerGroup.Controls.Add(cloudUrlLabel);

            cloudUrlText = CreateTextBox(126, 78, 272);
            cloudUrlText.Text = "https://api.openai.com/v1/chat/completions";
            providerGroup.Controls.Add(cloudUrlText);

            cloudModelLabel = CreatePlainLabel("", 412, 82, 44, 18);
            providerGroup.Controls.Add(cloudModelLabel);

            cloudModelText = CreateTextBox(462, 78, 140);
            cloudModelText.Text = "gpt-4.1-mini";
            providerGroup.Controls.Add(cloudModelText);

            cloudKeyLabel = CreatePlainLabel("", 36, 108, 82, 18);
            providerGroup.Controls.Add(cloudKeyLabel);

            cloudKeyText = CreateTextBox(126, 104, 272);
            cloudKeyText.UseSystemPasswordChar = true;
            providerGroup.Controls.Add(cloudKeyText);

            cloudKeyNotice = CreatePlainLabel("", 412, 100, 190, 30);
            providerGroup.Controls.Add(cloudKeyNotice);

            destinationGroup = CreateGroupBox("", 22, 434, 626, 78);
            Controls.Add(destinationGroup);

            installRoot = new TextBox();
            installRoot.Left = 14;
            installRoot.Top = 32;
            installRoot.Width = 500;
            installRoot.BorderStyle = BorderStyle.Fixed3D;
            installRoot.BackColor = XpWindow;
            installRoot.ForeColor = XpText;
            installRoot.Text = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Gwisp");
            destinationGroup.Controls.Add(installRoot);

            browseButton = CreateXpButton("...", 524, 29, 80, 26);
            browseButton.Click += BrowseButtonClick;
            destinationGroup.Controls.Add(browseButton);

            progressGroup = CreateGroupBox("", 22, 524, 626, 128);
            Controls.Add(progressGroup);

            progressBar = new ProgressBar();
            progressBar.Left = 14;
            progressBar.Top = 28;
            progressBar.Width = 598;
            progressBar.Height = 16;
            progressBar.Style = ProgressBarStyle.Marquee;
            progressBar.MarqueeAnimationSpeed = 0;
            progressGroup.Controls.Add(progressBar);

            logBox = new TextBox();
            logBox.Left = 14;
            logBox.Top = 54;
            logBox.Width = 598;
            logBox.Height = 58;
            logBox.Multiline = true;
            logBox.ScrollBars = ScrollBars.Vertical;
            logBox.ReadOnly = true;
            logBox.BorderStyle = BorderStyle.Fixed3D;
            logBox.BackColor = XpWindow;
            logBox.ForeColor = XpText;
            logBox.Font = new Font("Consolas", 9F, FontStyle.Regular);
            progressGroup.Controls.Add(logBox);

            Panel statusBar = CreateSunkenPanel(22, 662, 414, 24);
            Controls.Add(statusBar);

            statusLabel = new Label();
            statusLabel.Left = 6;
            statusLabel.Top = 4;
            statusLabel.Width = 398;
            statusLabel.Height = 16;
            statusLabel.BackColor = XpControl;
            statusBar.Controls.Add(statusLabel);

            installButton = CreateXpButton("", 458, 658, 190, 30);
            installButton.Font = new Font("Tahoma", 8F, FontStyle.Bold);
            installButton.Click += InstallButtonClick;
            Controls.Add(installButton);

            Label signature = new Label();
            signature.Text = SignatureText;
            signature.Left = 386;
            signature.Top = 690;
            signature.Width = 262;
            signature.Height = 18;
            signature.TextAlign = ContentAlignment.MiddleRight;
            signature.BackColor = XpControl;
            signature.ForeColor = Color.FromArgb(0, 51, 0);
            signature.Font = new Font("Consolas", 8F, FontStyle.Regular);
            Controls.Add(signature);

            ApplyLanguage();
            UpdateProviderPanelState();
        }

        private void LanguageSelectorChanged(object sender, EventArgs e)
        {
            if (languageSelector.SelectedIndex == 0)
            {
                currentLanguage = "en";
            }
            else if (languageSelector.SelectedIndex == 2)
            {
                currentLanguage = "de";
            }
            else
            {
                currentLanguage = "pt";
            }

            ApplyLanguage();
        }

        private void ApplyLanguage()
        {
            Text = Translate("windowTitle");
            titleLabel.Text = Translate("title");
            introLabel.Text = Translate("intro");
            languageLabel.Text = Translate("language");
            noticeLabel.Text = Translate("notice");
            choiceGroup.Text = Translate("choiceGroup");
            installBoth.Text = Translate("installBoth");
            installMain.Text = Translate("installMain");
            installSync.Text = Translate("installSync");
            providerGroup.Text = Translate("providerGroup");
            providerOllama.Text = Translate("providerOllama");
            providerCloud.Text = Translate("providerCloud");
            cloudUrlLabel.Text = Translate("cloudUrl");
            cloudModelLabel.Text = Translate("cloudModel");
            cloudKeyLabel.Text = Translate("cloudKey");
            cloudKeyNotice.Text = Translate("cloudKeyNotice");
            destinationGroup.Text = Translate("destination");
            progressGroup.Text = Translate("progress");
            installButton.Text = Translate("installButton");

            if (installButton.Enabled)
            {
                statusLabel.Text = Translate("ready");
            }
        }

        private void InstallChoiceChanged(object sender, EventArgs e)
        {
            UpdateProviderPanelState();
        }

        private void ProviderChanged(object sender, EventArgs e)
        {
            UpdateProviderPanelState();
        }

        private void BrowseButtonClick(object sender, EventArgs e)
        {
            using (FolderBrowserDialog dialog = new FolderBrowserDialog())
            {
                dialog.Description = Translate("chooseFolderDescription");
                dialog.SelectedPath = installRoot.Text;
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    installRoot.Text = dialog.SelectedPath;
                }
            }
        }

        private void InstallButtonClick(object sender, EventArgs e)
        {
            string root = installRoot.Text.Trim();
            if (root.Length == 0)
            {
                ShowInstallerDialog(Translate("setupTitle"), Translate("chooseFolder"));
                return;
            }

            string llmProvider = providerCloud.Checked ? "cloud" : "ollama";
            string cloudApiUrl = cloudUrlText.Text.Trim();
            string cloudModel = cloudModelText.Text.Trim();
            string cloudApiKey = cloudKeyText.Text.Trim();
            if (InstallsMainApp() && string.Equals(llmProvider, "cloud", StringComparison.OrdinalIgnoreCase))
            {
                if (!Uri.IsWellFormedUriString(cloudApiUrl, UriKind.Absolute))
                {
                    ShowInstallerDialog(Translate("setupTitle"), Translate("invalidCloudUrl"));
                    return;
                }

                if (cloudModel.Length == 0)
                {
                    ShowInstallerDialog(Translate("setupTitle"), Translate("missingCloudModel"));
                    return;
                }
            }

            SetInstallingState(true);
            logBox.Clear();

            InstallChoice choice = GetChoice();
            string selectedLanguage = currentLanguage;
            Thread worker = new Thread(delegate()
            {
                try
                {
                    RunInstall(choice, root, selectedLanguage, llmProvider, cloudApiUrl, cloudModel, cloudApiKey);
                    Ui(delegate()
                    {
                        statusLabel.Text = Translate("doneStatus");
                        ShowInstallerDialog(
                            Translate("setupTitle"),
                            Translate("doneMessage"));
                    });
                }
                catch (Exception ex)
                {
                    Log(Translate("errorPrefix") + ": " + ex.Message);
                    Ui(delegate()
                    {
                        statusLabel.Text = Translate("failedStatus");
                        ShowInstallerDialog(Translate("setupTitle"), ex.Message);
                    });
                }
                finally
                {
                    Ui(delegate() { SetInstallingState(false); });
                }
            });

            worker.IsBackground = true;
            worker.Start();
        }

        private InstallChoice GetChoice()
        {
            if (installMain.Checked)
            {
                return InstallChoice.Main;
            }

            if (installSync.Checked)
            {
                return InstallChoice.SyncOcr;
            }

            return InstallChoice.Both;
        }

        private bool InstallsMainApp()
        {
            return !installSync.Checked;
        }

        private void UpdateProviderPanelState()
        {
            bool canChooseProvider = InstallsMainApp() && installButton.Enabled;
            bool canEditCloud = canChooseProvider && providerCloud.Checked;

            providerGroup.Enabled = canChooseProvider;
            providerOllama.Enabled = canChooseProvider;
            providerCloud.Enabled = canChooseProvider;
            cloudUrlLabel.Enabled = canEditCloud;
            cloudUrlText.Enabled = canEditCloud;
            cloudModelLabel.Enabled = canEditCloud;
            cloudModelText.Enabled = canEditCloud;
            cloudKeyLabel.Enabled = canEditCloud;
            cloudKeyText.Enabled = canEditCloud;
            cloudKeyNotice.Enabled = canEditCloud;
        }

        private void RunInstall(
            InstallChoice choice,
            string root,
            string selectedLanguage,
            string llmProvider,
            string cloudApiUrl,
            string cloudModel,
            string cloudApiKey)
        {
            Directory.CreateDirectory(root);

            string workRoot = Path.Combine(
                Path.GetTempPath(),
                "GwispSetup",
                Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(workRoot);

            try
            {
                if (choice == InstallChoice.Both || choice == InstallChoice.Main)
                {
                    InstallPackage(
                        MainZipName,
                        "Install-Gwisp-Main.ps1",
                        Path.Combine(root, "Main"),
                        workRoot,
                        selectedLanguage,
                        true,
                        llmProvider,
                        cloudApiUrl,
                        cloudModel,
                        cloudApiKey);
                }

                if (choice == InstallChoice.Both || choice == InstallChoice.SyncOcr)
                {
                    InstallPackage(
                        SyncZipName,
                        "Install-Gwisp-SyncOCR.ps1",
                        Path.Combine(root, "SyncOCR"),
                        workRoot,
                        selectedLanguage,
                        false,
                        llmProvider,
                        cloudApiUrl,
                        cloudModel,
                        cloudApiKey);
                }
            }
            finally
            {
                TryDeleteDirectory(workRoot);
            }
        }

        private void InstallPackage(
            string zipName,
            string installerScriptName,
            string targetDirectory,
            string workRoot,
            string selectedLanguage,
            bool configureProvider,
            string llmProvider,
            string cloudApiUrl,
            string cloudModel,
            string cloudApiKey)
        {
            Log(Translate("preparing") + " " + zipName + "...");
            string zipPath = ResolvePackage(zipName, workRoot);
            string extractDir = Path.Combine(workRoot, Path.GetFileNameWithoutExtension(zipName));

            VerifyPackageHash(zipPath, zipName);
            Directory.CreateDirectory(extractDir);
            ExtractZipSafely(zipPath, extractDir);

            string installerScript = Path.Combine(extractDir, installerScriptName);
            if (!File.Exists(installerScript))
            {
                throw new InvalidOperationException(Translate("missingInstaller") + ": " + installerScriptName);
            }

            Log(Translate("installingTo") + " " + targetDirectory + "...");
            RunPowerShellInstaller(
                installerScript,
                targetDirectory,
                selectedLanguage,
                configureProvider,
                llmProvider,
                cloudApiUrl,
                cloudModel,
                cloudApiKey);
            Log(Translate("completed") + ": " + targetDirectory);
        }

        private string ResolvePackage(string zipName, string workRoot)
        {
            string localZip = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, zipName);
            if (File.Exists(localZip))
            {
                Log(Translate("localPackage") + ": " + localZip);
                return localZip;
            }

            string downloadUrl = BuildPackageUrl(zipName);
            string destination = Path.Combine(workRoot, zipName);
            Log(Translate("downloading") + ": " + downloadUrl);

            using (WebClient client = new WebClient())
            {
                client.Headers.Add("User-Agent", "GwispSetup");
                client.DownloadFile(downloadUrl, destination);
            }

            return destination;
        }

        private static string BuildPackageUrl(string zipName)
        {
            return DefaultReleaseBaseUrl.TrimEnd('/') + "/" + zipName;
        }

        private void VerifyPackageHash(string zipPath, string zipName)
        {
            string expectedHash = GetExpectedPackageHash(zipName);
            if (string.IsNullOrWhiteSpace(expectedHash))
            {
                return;
            }

            string actualHash = ComputeSha256(zipPath);
            if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(Translate("hashMismatch") + ": " + zipName);
            }

            Log(Translate("hashVerified") + ": " + zipName);
        }

        private static string GetExpectedPackageHash(string zipName)
        {
            if (string.Equals(zipName, MainZipName, StringComparison.OrdinalIgnoreCase))
            {
                return MainZipSha256;
            }

            if (string.Equals(zipName, SyncZipName, StringComparison.OrdinalIgnoreCase))
            {
                return SyncZipSha256;
            }

            return string.Empty;
        }

        private static string ComputeSha256(string filePath)
        {
            using (SHA256 sha256 = SHA256.Create())
            using (FileStream stream = File.OpenRead(filePath))
            {
                byte[] hash = sha256.ComputeHash(stream);
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
        }

        private static void ExtractZipSafely(string zipPath, string extractDir)
        {
            string fullExtractDir = Path.GetFullPath(extractDir + Path.DirectorySeparatorChar);

            using (ZipArchive archive = ZipFile.OpenRead(zipPath))
            {
                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    string destinationPath = Path.GetFullPath(Path.Combine(extractDir, entry.FullName));
                    if (!destinationPath.StartsWith(fullExtractDir, StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException("Pacote ZIP contem caminho inseguro: " + entry.FullName);
                    }

                    if (string.IsNullOrEmpty(entry.Name))
                    {
                        Directory.CreateDirectory(destinationPath);
                        continue;
                    }

                    string destinationDirectory = Path.GetDirectoryName(destinationPath);
                    if (!string.IsNullOrEmpty(destinationDirectory))
                    {
                        Directory.CreateDirectory(destinationDirectory);
                    }

                    entry.ExtractToFile(destinationPath, true);
                }
            }
        }

        private void RunPowerShellInstaller(
            string scriptPath,
            string targetDirectory,
            string selectedLanguage,
            bool configureProvider,
            string llmProvider,
            string cloudApiUrl,
            string cloudModel,
            string cloudApiKey)
        {
            ProcessStartInfo startInfo = new ProcessStartInfo();
            startInfo.FileName = GetPowerShellPath();
            StringBuilder arguments = new StringBuilder();
            arguments.Append("-NoProfile -ExecutionPolicy Bypass -File ");
            arguments.Append(Quote(scriptPath));
            arguments.Append(" -InstallDir ");
            arguments.Append(Quote(targetDirectory));
            arguments.Append(" -Language ");
            arguments.Append(Quote(selectedLanguage));

            if (configureProvider)
            {
                arguments.Append(" -LlmProvider ");
                arguments.Append(Quote(llmProvider));

                if (!string.IsNullOrEmpty(cloudApiUrl))
                {
                    arguments.Append(" -CloudApiUrl ");
                    arguments.Append(Quote(cloudApiUrl));
                }

                if (!string.IsNullOrEmpty(cloudModel))
                {
                    arguments.Append(" -CloudModel ");
                    arguments.Append(Quote(cloudModel));
                }

            }

            startInfo.Arguments = arguments.ToString();
            startInfo.UseShellExecute = false;
            startInfo.RedirectStandardOutput = true;
            startInfo.RedirectStandardError = true;
            startInfo.CreateNoWindow = true;
            if (configureProvider && !string.IsNullOrEmpty(cloudApiKey))
            {
                startInfo.EnvironmentVariables["GWISP_SETUP_CLOUD_API_KEY"] = cloudApiKey;
            }

            using (Process process = new Process())
            using (ManualResetEvent outputClosed = new ManualResetEvent(false))
            using (ManualResetEvent errorClosed = new ManualResetEvent(false))
            {
                process.StartInfo = startInfo;
                process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e)
                {
                    if (e.Data == null)
                    {
                        outputClosed.Set();
                    }
                    else
                    {
                        Log(e.Data);
                    }
                };
                process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e)
                {
                    if (e.Data == null)
                    {
                        errorClosed.Set();
                    }
                    else
                    {
                        Log(e.Data);
                    }
                };

                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                process.WaitForExit();
                outputClosed.WaitOne();
                errorClosed.WaitOne();

                if (process.ExitCode != 0)
                {
                    throw new InvalidOperationException(
                        Translate("powershellReturned") +
                        " " +
                        process.ExitCode +
                        " " +
                        Path.GetFileName(scriptPath));
                }
            }
        }

        private static string GetPowerShellPath()
        {
            string path = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                @"WindowsPowerShell\v1.0\powershell.exe");
            return File.Exists(path) ? path : "powershell.exe";
        }

        private static string Quote(string value)
        {
            return "'" + value.Replace("'", "''") + "'";
        }

        private void SetInstallingState(bool installing)
        {
            installBoth.Enabled = !installing;
            installMain.Enabled = !installing;
            installSync.Enabled = !installing;
            languageSelector.Enabled = !installing;
            installRoot.Enabled = !installing;
            browseButton.Enabled = !installing;
            installButton.Enabled = !installing;
            UpdateProviderPanelState();
            progressBar.MarqueeAnimationSpeed = installing ? 30 : 0;
            statusLabel.Text = installing ? Translate("installing") : statusLabel.Text;
        }

        private string Translate(string key)
        {
            if (string.Equals(currentLanguage, "en", StringComparison.OrdinalIgnoreCase))
            {
                switch (key)
                {
                    case "setupTitle":
                        return "Gwisp Setup";
                    case "windowTitle":
                    case "title":
                        return "Gwisp Setup - " + VersionLabel;
                    case "intro":
                        return "Alpha build 1.0.3. Windows 11 tested installer for Main, Sync OCR, or both.";
                    case "language":
                        return "Language";
                    case "notice":
                        return "Choose components and AI provider. The EXE uses local ZIPs beside it or downloads from GitHub Release.";
                    case "choiceGroup":
                        return "Install option";
                    case "installBoth":
                        return "Both: full main app + Sync OCR";
                    case "installMain":
                        return "Only the full main app";
                    case "installSync":
                        return "Only Sync OCR";
                    case "providerGroup":
                        return "AI provider for Gwisp Main";
                    case "providerOllama":
                        return "Local Ollama (default; keeps AI requests local)";
                    case "providerCloud":
                        return "Cloud API (Chat Completions compatible)";
                    case "cloudUrl":
                        return "API URL";
                    case "cloudModel":
                        return "Model";
                    case "cloudKey":
                        return "API key";
                    case "cloudKeyNotice":
                        return "Saved only in local config.json. Leave blank to use GWISP_CLOUD_API_KEY.";
                    case "destination":
                        return "Destination";
                    case "progress":
                        return "Progress";
                    case "ready":
                        return "Ready to install.";
                    case "installButton":
                        return "Download and install";
                    case "chooseFolderDescription":
                    case "chooseFolder":
                        return "Choose an install folder.";
                    case "invalidCloudUrl":
                        return "Enter a valid Cloud API URL.";
                    case "missingCloudModel":
                        return "Enter a Cloud API model name.";
                    case "installing":
                        return "Installing...";
                    case "doneStatus":
                        return "Installation complete.";
                    case "doneMessage":
                        return "Installation complete. Open the Run-Gwisp-*.bat launcher from the selected install folder.";
                    case "failedStatus":
                        return "Installation failed.";
                    case "preparing":
                        return "Preparing";
                    case "missingInstaller":
                        return "Installer not found inside package";
                    case "installingTo":
                        return "Installing to";
                    case "completed":
                        return "Completed";
                    case "localPackage":
                        return "Using local package";
                    case "downloading":
                        return "Downloading";
                    case "hashVerified":
                        return "SHA-256 verified";
                    case "hashMismatch":
                        return "Package integrity check failed";
                    case "powershellReturned":
                        return "PowerShell returned code";
                    case "errorPrefix":
                        return "ERROR";
                }
            }

            if (string.Equals(currentLanguage, "de", StringComparison.OrdinalIgnoreCase))
            {
                switch (key)
                {
                    case "setupTitle":
                        return "Gwisp Setup";
                    case "windowTitle":
                    case "title":
                        return "Gwisp Setup - " + VersionLabel;
                    case "intro":
                        return "Alpha build 1.0.3. Unter Windows 11 getesteter Installer fuer Main, Sync OCR oder beides.";
                    case "language":
                        return "Sprache";
                    case "notice":
                        return "Komponenten und KI-Anbieter waehlen. Die EXE nutzt lokale ZIPs oder GitHub Release.";
                    case "choiceGroup":
                        return "Installationsoption";
                    case "installBoth":
                        return "Beides: komplette Haupt-App + Sync OCR";
                    case "installMain":
                        return "Nur komplette Haupt-App";
                    case "installSync":
                        return "Nur Sync OCR";
                    case "providerGroup":
                        return "KI-Anbieter fuer Gwisp Main";
                    case "providerOllama":
                        return "Lokales Ollama (Standard; KI-Anfragen bleiben lokal)";
                    case "providerCloud":
                        return "Cloud API (kompatibel mit Chat Completions)";
                    case "cloudUrl":
                        return "API-URL";
                    case "cloudModel":
                        return "Modell";
                    case "cloudKey":
                        return "API-Key";
                    case "cloudKeyNotice":
                        return "Nur in lokaler config.json gespeichert. Leer lassen fuer GWISP_CLOUD_API_KEY.";
                    case "destination":
                        return "Zielordner";
                    case "progress":
                        return "Fortschritt";
                    case "ready":
                        return "Bereit zur Installation.";
                    case "installButton":
                        return "Herunterladen und installieren";
                    case "chooseFolderDescription":
                    case "chooseFolder":
                        return "Installationsordner waehlen.";
                    case "invalidCloudUrl":
                        return "Geben Sie eine gueltige Cloud-API-URL ein.";
                    case "missingCloudModel":
                        return "Geben Sie einen Cloud-API-Modellnamen ein.";
                    case "installing":
                        return "Installiere...";
                    case "doneStatus":
                        return "Installation abgeschlossen.";
                    case "doneMessage":
                        return "Installation abgeschlossen. Starten Sie Run-Gwisp-*.bat aus dem gewaehlten Installationsordner.";
                    case "failedStatus":
                        return "Installation fehlgeschlagen.";
                    case "preparing":
                        return "Vorbereiten";
                    case "missingInstaller":
                        return "Installer im Paket nicht gefunden";
                    case "installingTo":
                        return "Installiere nach";
                    case "completed":
                        return "Abgeschlossen";
                    case "localPackage":
                        return "Lokales Paket verwenden";
                    case "downloading":
                        return "Herunterladen";
                    case "hashVerified":
                        return "SHA-256 geprueft";
                    case "hashMismatch":
                        return "Paket-Integritaetspruefung fehlgeschlagen";
                    case "powershellReturned":
                        return "PowerShell gab Code zurueck";
                    case "errorPrefix":
                        return "FEHLER";
                }
            }

            switch (key)
            {
                case "setupTitle":
                    return "Gwisp Setup";
                case "windowTitle":
                case "title":
                    return "Gwisp Setup - " + VersionLabel;
                case "intro":
                    return "Alpha build 1.0.3. Instalador testado no Windows 11 para Main, Sync OCR ou os dois.";
                case "language":
                    return "Idioma";
                case "notice":
                    return "Escolha componentes e provedor de IA. O EXE usa ZIPs locais ao lado dele ou baixa da GitHub Release.";
                case "choiceGroup":
                    return "Opcao de instalacao";
                case "installBoth":
                    return "Os dois: app principal completo + Sync OCR";
                case "installMain":
                    return "Somente app principal completo";
                case "installSync":
                    return "Somente Sync OCR";
                case "providerGroup":
                    return "Provedor de IA do Gwisp Main";
                case "providerOllama":
                    return "Ollama local (padrao; requisicoes de IA ficam locais)";
                case "providerCloud":
                    return "Cloud API (compativel com Chat Completions)";
                case "cloudUrl":
                    return "API URL";
                case "cloudModel":
                    return "Modelo";
                case "cloudKey":
                    return "API key";
                case "cloudKeyNotice":
                    return "Salva so no config.json local. Vazio usa GWISP_CLOUD_API_KEY.";
                case "destination":
                    return "Destino";
                case "progress":
                    return "Progresso";
                case "ready":
                    return "Pronto para instalar.";
                case "installButton":
                    return "Baixar e instalar";
                case "chooseFolderDescription":
                case "chooseFolder":
                    return "Escolha uma pasta de instalacao.";
                case "invalidCloudUrl":
                    return "Informe uma URL valida para a Cloud API.";
                case "missingCloudModel":
                    return "Informe o nome do modelo da Cloud API.";
                case "installing":
                    return "Instalando...";
                case "doneStatus":
                    return "Instalacao concluida.";
                case "doneMessage":
                    return "Instalacao concluida. Abra o launcher Run-Gwisp-*.bat na pasta de instalacao escolhida.";
                case "failedStatus":
                    return "Instalacao falhou.";
                case "preparing":
                    return "Preparando";
                case "missingInstaller":
                    return "Instalador nao encontrado dentro do pacote";
                case "installingTo":
                    return "Instalando em";
                case "completed":
                    return "Concluido";
                case "localPackage":
                    return "Usando pacote local";
                case "downloading":
                    return "Baixando";
                case "hashVerified":
                    return "SHA-256 verificado";
                case "hashMismatch":
                    return "Falha na verificacao de integridade do pacote";
                case "powershellReturned":
                    return "PowerShell retornou codigo";
                case "errorPrefix":
                    return "ERRO";
            }

            return key;
        }

        private void ShowInstallerDialog(string title, string message)
        {
            using (XpDialog dialog = new XpDialog(title, message, appIcon))
            {
                dialog.ShowDialog(this);
            }
        }

        private void Log(string message)
        {
            Ui(delegate()
            {
                logBox.AppendText(DateTime.Now.ToString("HH:mm:ss") + "  " + message + Environment.NewLine);
            });
        }

        private void Ui(Action action)
        {
            if (IsDisposed)
            {
                return;
            }

            if (InvokeRequired)
            {
                BeginInvoke(action);
            }
            else
            {
                action();
            }
        }

        private static Icon LoadSetupIcon()
        {
            try
            {
                Icon icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
                return icon ?? SystemIcons.Application;
            }
            catch
            {
                return SystemIcons.Application;
            }
        }

        private static GroupBox CreateGroupBox(string text, int left, int top, int width, int height)
        {
            GroupBox groupBox = new GroupBox();
            groupBox.Text = text;
            groupBox.Left = left;
            groupBox.Top = top;
            groupBox.Width = width;
            groupBox.Height = height;
            groupBox.BackColor = XpControl;
            groupBox.ForeColor = XpText;
            return groupBox;
        }

        private static RadioButton CreateRadioButton(string text, int left, int top, bool isChecked)
        {
            RadioButton radio = new RadioButton();
            radio.Text = text;
            radio.Left = left;
            radio.Top = top;
            radio.Width = 570;
            radio.Height = 22;
            radio.BackColor = XpControl;
            radio.ForeColor = XpText;
            radio.Checked = isChecked;
            return radio;
        }

        private static Button CreateXpButton(string text, int left, int top, int width, int height)
        {
            Button button = new Button();
            button.Text = text;
            button.Left = left;
            button.Top = top;
            button.Width = width;
            button.Height = height;
            button.BackColor = XpControl;
            button.ForeColor = XpText;
            button.FlatStyle = FlatStyle.Standard;
            button.UseVisualStyleBackColor = false;
            return button;
        }

        private static Label CreatePlainLabel(string text, int left, int top, int width, int height)
        {
            Label label = new Label();
            label.Text = text;
            label.Left = left;
            label.Top = top;
            label.Width = width;
            label.Height = height;
            label.BackColor = XpControl;
            label.ForeColor = XpText;
            return label;
        }

        private static TextBox CreateTextBox(int left, int top, int width)
        {
            TextBox textBox = new TextBox();
            textBox.Left = left;
            textBox.Top = top;
            textBox.Width = width;
            textBox.Height = 22;
            textBox.BorderStyle = BorderStyle.Fixed3D;
            textBox.BackColor = XpWindow;
            textBox.ForeColor = XpText;
            return textBox;
        }

        private static Label CreateInfoLabel(string text)
        {
            Label label = new Label();
            label.Text = text;
            label.BackColor = XpInfo;
            label.ForeColor = XpText;
            label.BorderStyle = BorderStyle.FixedSingle;
            label.TextAlign = ContentAlignment.MiddleLeft;
            label.Padding = new Padding(6, 0, 6, 0);
            return label;
        }

        private static Panel CreateRaisedPanel(int left, int top, int width, int height)
        {
            Panel panel = new Panel();
            panel.Left = left;
            panel.Top = top;
            panel.Width = width;
            panel.Height = height;
            panel.BackColor = XpControl;
            panel.BorderStyle = BorderStyle.Fixed3D;
            return panel;
        }

        private static Panel CreateSunkenPanel(int left, int top, int width, int height)
        {
            Panel panel = new Panel();
            panel.Left = left;
            panel.Top = top;
            panel.Width = width;
            panel.Height = height;
            panel.BackColor = XpControl;
            panel.BorderStyle = BorderStyle.Fixed3D;
            return panel;
        }

        private static void TryDeleteDirectory(string directory)
        {
            try
            {
                if (Directory.Exists(directory))
                {
                    Directory.Delete(directory, true);
                }
            }
            catch
            {
                // Temporary files are best-effort cleanup.
            }
        }
    }

    internal sealed class XpDialog : Form
    {
        private static readonly Color XpControl = Color.FromArgb(236, 233, 216);
        private static readonly Color XpInfo = Color.FromArgb(255, 255, 225);
        private static readonly Color XpText = Color.Black;

        public XpDialog(string title, string message, Icon appIcon)
        {
            Text = title;
            Icon = appIcon;
            ShowIcon = true;
            Width = 440;
            Height = 180;
            Font = new Font("Tahoma", 8F, FontStyle.Regular);
            BackColor = XpControl;
            ForeColor = XpText;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            PictureBox iconBox = new PictureBox();
            iconBox.Left = 18;
            iconBox.Top = 22;
            iconBox.Width = 34;
            iconBox.Height = 34;
            iconBox.SizeMode = PictureBoxSizeMode.CenterImage;
            iconBox.Image = appIcon.ToBitmap();
            Controls.Add(iconBox);

            Label messageLabel = new Label();
            messageLabel.Left = 66;
            messageLabel.Top = 20;
            messageLabel.Width = 334;
            messageLabel.Height = 64;
            messageLabel.Text = message;
            messageLabel.BackColor = XpInfo;
            messageLabel.BorderStyle = BorderStyle.FixedSingle;
            messageLabel.Padding = new Padding(6);
            Controls.Add(messageLabel);

            Button okButton = new Button();
            okButton.Text = "OK";
            okButton.Left = 318;
            okButton.Top = 104;
            okButton.Width = 82;
            okButton.Height = 26;
            okButton.BackColor = XpControl;
            okButton.UseVisualStyleBackColor = false;
            okButton.DialogResult = DialogResult.OK;
            Controls.Add(okButton);

            AcceptButton = okButton;
        }
    }
}
