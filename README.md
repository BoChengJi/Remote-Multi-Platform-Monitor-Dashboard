🖥️ Remote Multi-Platform Monitor Dashboard
跨平台的系統監控平台，支援 Linux / Windows / macOS 主機，透過 Flask 建立後端 API 與儀表板前端，整合 SSH / WinRM 實時取得主機的 CPU、記憶體、磁碟、網路使用率資訊。

📸 範例畫面

🚀 功能特色
✅ 支援 Linux、Windows、macOS 主機

✅ 即時獲取 CPU / Memory / Disk / Network 使用率

✅ 使用 Flask 架設 Web API 與儀表板

✅ 使用 SSH（paramiko） / WinRM（pywinrm） 連線主機

✅ 支援 Chart.js 顯示即時網路傳輸速率圖表

✅ 多主機資料並行獲取（threading）

📂 專案結構
csharp
複製
編輯
project/  
├── app.py                # Flask 後端主程式  
├── settings.ini          # 主機設定檔  
├── templates/  
│   └── dashboard.html    # 儀表板 HTML 前端  
├── static/               # (可選) CSS/JS 資源  
├── README.md             # 使用說明文件
🧩 安裝說明
✅ 安裝環境
Python 3.8+

已安裝的系統工具：Linux/macOS 需支援 SSH；Windows 主機需啟用 WinRM

✅ 安裝套件
bash
複製
編輯
pip install flask paramiko pywinrm
⚙️ 設定主機資訊：settings.ini
ini
複製
編輯
[hosts]
host1 = 192.168.1.101, linux
host2 = 192.168.1.102, windows
host3 = 192.168.1.103, macos
每台主機一行，格式：IP位址, 作業系統
OS 必須為：linux, windows, macos

🔐 設定帳密
在 MonitorManager 內修改預設帳號密碼：

python
複製
編輯
self.default_linux_user = 'your_linux_user'
self.default_linux_pass = 'your_linux_password'
self.default_windows_user = 'your_windows_user'
self.default_windows_pass = 'your_windows_password'
▶️ 啟動伺服器
bash
複製
編輯
python app.py
開啟瀏覽器進入：

arduino
複製
編輯
http://localhost:5000
📡 API 範例
/api/status
回傳 JSON 格式的即時狀態：

json
複製
編輯
[
  {
    "timestamp": "2025-07-06T12:00:00",
    "host": "192.168.1.101",
    "os": "linux",
    "cpu_percent": 20.5,
    "memory": {
      "total": 8388608000,
      "used": 4194304000,
      "percent": 50.0
    },
    "disk": {
      "total": "50G",
      "used": "25G",
      "percent": 50
    },
    "gpu": [],
    "network": {
      "bytes_sent": 123456789,
      "bytes_recv": 987654321
    }
  }
]
🧠 可擴充功能建議
功能	方法
GPU 使用率	使用 nvidia-smi 或 Windows WMI
即時資料推播	整合 WebSocket
登入驗證	使用 Flask-Login 或 JWT
Docker 化	建立 Dockerfile 與 docker-compose.yml
儀表板美化	加入圖示、主機狀態顏色變化、Chart.js 加強

🛠️ 系統相依需求
OS	連線方式	相依需求
Linux / macOS	SSH	啟用 SSH Server，並允許帳密登入
Windows	WinRM	啟用 WinRM、設定 Basic Auth 支援

✅ 安全建議
請避免使用明碼儲存帳密，可整合 .env 檔或加密憑證管理

限制 Flask 僅在內網可存取，或使用 Nginx 反代與憑證加密

日後可改為 SSH Key / Kerberos 等更安全認證方式

📜 授權
本專案以 MIT License 授權，你可以自由修改與商用。