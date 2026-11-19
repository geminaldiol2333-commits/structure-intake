# Installs Python 3.14, the CUDA build of PyTorch, the recognition packages,
# and the two model checkpoints. Safe to run again.
$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $PSScriptRoot
$VbsDir = Join-Path $AppRoot "scratch\intake-v0.1"
$ModelDir = Join-Path $env:LOCALAPPDATA "StructureIntake\models"
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

function Find-Python {
    $candidates = @(
        "C:\Python314\python.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $prefix = & py -3.14 -c "import sys; print(sys.base_prefix)" 2>$null
        if ($prefix) {
            $exe = Join-Path $prefix.Trim() "python.exe"
            if (Test-Path $exe) { return $exe }
        }
    }
    return $null
}

function Install-Python {
    Write-Host "正在安装 Python 3.14 ..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "没有找到 winget，也没有 Python 3.14。请先安装 Python 3.14（勾选 Add python.exe to PATH），然后重新运行这个脚本。"
    }
    & winget install --id Python.Python.3.14 -e --scope user --accept-package-agreements --accept-source-agreements
    return Find-Python
}

function Copy-Or-Download($Name, $Url, $Legacy) {
    $dest = Join-Path $ModelDir $Name
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 500MB)) {
        Write-Host "模型已在 $dest"
        return
    }
    if ($Legacy -and (Test-Path $Legacy) -and ((Get-Item $Legacy).Length -gt 500MB)) {
        Write-Host "本机已有模型，跳过下载：$Legacy"
        return
    }
    Write-Host "正在下载 $Name （约 1 GB）..."
    $part = "$dest.part"
    & curl.exe -L --fail --retry 3 --progress-bar -o $part $Url
    if ($LASTEXITCODE -ne 0) { throw "下载失败：$Url" }
    Move-Item -Force $part $dest
    Write-Host "已保存 $dest"
}

try {
    $python = Find-Python
    if (-not $python) { $python = Install-Python }
    if (-not $python) { throw "安装之后仍然找不到 Python 3.14。" }
    $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
    if (-not (Test-Path $pythonw)) { throw "找到了 $python，但没有 pythonw.exe。" }
    Set-Content -Path (Join-Path $VbsDir "pythonw.path") -Value $pythonw -Encoding ascii
    Write-Host "Python: $pythonw"

    $cuda = & $python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "正在安装 CUDA 版 PyTorch ..."
        & $python -m pip install --upgrade pip
        & $python -m pip install torch --index-url https://download.pytorch.org/whl/cu130
    } else {
        Write-Host "PyTorch CUDA 已可用。"
    }

    $req = Join-Path $AppRoot "requirements.txt"
    Write-Host "正在安装识别依赖 ..."
    & $python -m pip install -r $req
    if ($LASTEXITCODE -ne 0) { throw "pip 安装失败。" }

    & $python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖把 PyTorch 换成了 CPU 版，正在装回 CUDA 版 ..."
        & $python -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu130
    }

    & $python -c "import fitz, cv2, webview, win32com.client, rdkit, MolNexTR, molscribe"
    if ($LASTEXITCODE -ne 0) { throw "依赖导入失败。可以再运行一次 installer\准备依赖.ps1。" }

    Copy-Or-Download "molnextr_best.pth" `
        "https://huggingface.co/datasets/CYF200127/MolNexTR/resolve/main/molnextr_best.pth" `
        "D:\AI_Tools\models\MolNexTR\molnextr_best.pth"
    Copy-Or-Download "swin_base_char_aux_1m680k.pth" `
        "https://huggingface.co/yujieq/MolScribe/resolve/main/swin_base_char_aux_1m680k.pth" `
        "D:\AI_Tools\models\MolScribe\swin_base_char_aux_1m680k.pth"

    Write-Host ""
    Write-Host "准备完成。可以从开始菜单或桌面打开「结构式提取」。"
    Write-Host "重绘需要本机已经安装 ChemDraw。"
}
catch {
    Write-Host ""
    Write-Host "准备没有完成：$($_.Exception.Message)" -ForegroundColor Red
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "依赖没有准备完：$($_.Exception.Message)`r`n`r`n可以稍后再次运行安装目录里的 installer\准备依赖.ps1。",
        "结构式提取",
        "OK",
        "Warning"
    ) | Out-Null
}
