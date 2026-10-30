# GitHub upload + Windows build

Target repository: **https://github.com/Bossyfkbear/J-APP**. This repository was **public** at last check; uploading this source publishes it. The ChatGPT GitHub connector's write action was blocked by GitHub HTTP 403 despite allowing repository reads. This helper instead uses **your own authenticated GitHub CLI** on your Windows PC. Never paste passwords or access tokens into chat.

1. Install [Git for Windows](https://git-scm.com/downloads/win) and [GitHub CLI](https://cli.github.com/), if not already installed.
2. Unzip this archive. Open the **`AudioPostToolkit`** folder and double-click **`publish_and_build_windows.bat`**.
3. Complete the official GitHub browser sign-in when prompted, selecting the `Bossyfkbear` account. The script checks the login and the repository's push permission.
4. The script creates only local Git metadata, commits the project files, **never uses a force push**, uploads to `main`, requests **Windows development build**, watches the result, and on success downloads the ZIP and SHA256 into `windows-build-artifact/`.
5. If a command fails, copy its **error message (without authentication secrets)** for debugging. The remote repository is never overwritten by force.

This workflow is unnecessary if ChatGPT's GitHub App installation is fixed to authorize write access in the `Bossyfkbear` account. The CI build validates Python tests, freezes the GUI, runs the frozen GUI panel initialization diagnostic, and packages the executable folder. It does **not** certify real Windows audio-device playback, sound quality, or optional model installation. FFmpeg, FFprobe and FFplay still need to be available on the user's Windows system, or placed alongside the compiled EXE.
