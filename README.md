# PDF 大師（PDF Master）

以 Python + Tkinter + PyMuPDF 打造的 Windows 桌面 PDF 工具。載入多份 PDF 後，以縮圖牆檢視所有頁面，直接框選頁面做合併、重排、旋轉、加密、浮水印、簽名等處理。

介面為繁體中文。

## 功能

**頁面操作**

- 拖放或開啟多份 PDF，所有頁面以縮圖牆統一呈現
- 跨檔案合併：把多份 PDF 的頁面混編成一份
- 選取頁面後刪除、提取另存、左右旋轉 90 度
- 拖曳調整頁面順序

**內容加工**

- 文字浮水印（斜向、可調字級與透明度）
- 簽名圖章：載入透明 PNG 簽名檔，縮放定位後蓋到指定頁
- 向量符號：以 PyMuPDF 繪圖 API 直接畫出符號，不失真
- 頁碼：自訂位置、起始號碼、格式
- 裁切：以點（point）為單位修邊，72 點等於 1 英吋

**檔案處理**

- 加密：設定使用者密碼與擁有者密碼
- 解密：輸入密碼開啟受保護的 PDF，另存無密碼版本
- 壓縮：重新儲存並回收無用物件
- PDF 轉圖片：批次輸出指定頁為 PNG／JPG
- 圖片轉 PDF：把 PNG、JPG、BMP、TIFF、GIF、WebP 併成一份 PDF

## 安裝

需要 Windows 與 Python 3.12（其他 3.x 版本理論可行，但本專案只在 3.12 驗證過）。

```bash
pip install -r requirements.txt
```

直接執行：

```bash
python app.py
```

## 用 start.bat 啟動（無主控台視窗）

`start.bat` 會用一份改名的 `pythonw.exe` 副本啟動程式，讓工作管理員與 `taskkill` 能單獨辨識這支程式，不會誤殺其他 Python 程序。這些副本是本機檔案，不隨 repo 發佈，第一次使用先執行：

```bash
relink_launcher.bat
```

它會自動偵測系統上的 Python 3.12，複製出 `pythonw_pdfmaster.exe`、`python312.dll`、`python3.dll` 三個檔案。完成後即可用 `start.bat` 啟動、`stop.bat` 關閉。

程式的執行日誌寫在 `~/.pdfmaster/app.log`。

## 專案結構

| 檔案 | 內容 |
|------|------|
| `app.py` | 主視窗、縮圖牆、工具列、所有操作的流程控制 |
| `pdf_engine.py` | 純 PyMuPDF 邏輯層，每個函式回傳新的 Document，不就地修改 |
| `dialogs.py` | 各功能的設定對話框，含可縮放預覽畫布 |
| `thumbnail_cache.py` | 縮圖 LRU 快取與背景算繪執行緒 |
| `launcher.py` | pythonw 啟動用的包裝層，在任何 import 之前先接管 stdout／stderr |

## 授權

本專案以 **GNU AGPL-3.0** 釋出，完整條款見 [LICENSE](LICENSE)。

選擇 AGPL 的原因：核心相依套件 PyMuPDF 採「AGPL-3.0 或 Artifex 商業授權」雙授權，衍生作品必須沿用相容授權。若你要把本專案用於封閉源碼的商業產品，需另行向 Artifex 取得 PyMuPDF 商業授權。

其餘相依套件：tkinterdnd2（MIT）、Pillow（MIT-CMU）。

製作者：黃政文
