# Google 廣東話輸入法 for Windows (PIME插件)
A tool which allows Google Cantonese Input on PC outside Chrome (targeting Windows 8+)  
唔駛喺 Chrome 入面都用到嘅 Google 廣東話輸入法 (Windows 8 以上)

## 功能
*   喺 Windows 入面使用廣東話輸入法，適用於大部分程式同遊戲，唔再局限喺手機同 Google Docs
*   完美支援 Windows 10
*   Shift 切換中英文, ← → 鍵選字, ↑ ↓ 鍵轉頁數, Space 確認
*   中文模式支援常用全形符號：，。「」『』！？——…… 等等

## 下載/安裝
*   **[[按此下載]](https://github.com/tinycrate/gcantonese-ime/releases/)**

    1.   揀最新版本
    2.   跟從安裝指示

*   本輸入法不含惡意程式，Windows或者防毒軟件可能偶爾出現誤判，可安全忽略。

## PIME
本輸入法使用 [PIME](https://github.com/EasyIME/PIME) 輸入法框架作為開發平台，並以
[LGPLv2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html) 形式獲得授權。
你可以 [按此](https://github.com/EasyIME/PIME) 取得 PIME 的原始碼以及編譯方式 。

### 將本輸入法增加至現有 PIME 安裝
如果你已是 PIME 使用者，或者安裝了更新版本的 PIME，你可以手動將此輸入法加入 PIME。

1. `git clone` 或者 [直接下載](https://github.com/tinycrate/gcantonese-ime/archive/master.zip) 此 repo
2. 將整個資料夾 `gcantonese` 複製到 `C:\Program Files (x86)\PIME\python\input_methods\`
3. 用 *系統管理員模式* 開啟 `cmd`，執行以下命令：

    ```
    regsvr32 /u "C:\Program Files (X86)\PIME\x86\PIMETextService.dll"
    regsvr32 /u "C:\Program Files (X86)\PIME\x64\PIMETextService.dll"
    regsvr32 "C:\Program Files (X86)\PIME\x86\PIMETextService.dll"
    regsvr32 "C:\Program Files (X86)\PIME\x64\PIMETextService.dll"
    ```
    
    如果使用 32-bit Windows，請用以下命令代替：
    
    ```
    regsvr32 /u "C:\Program Files\PIME\x86\PIMETextService.dll"
    regsvr32 "C:\Program Files\PIME\x86\PIMETextService.dll"
    ```    
