import configparser
from flask import Flask, render_template, jsonify
from datetime import datetime
import paramiko
import winrm
import re
import threading

app = Flask(__name__)

config = configparser.ConfigParser()
config.read('settings.ini')

hosts = config['hosts']

# --- SSH (Linux) 監控類別 ---
class LinuxMonitor:
    def __init__(self, ip, username='user', password='pass'):
        self.ip = ip
        self.username = username
        self.password = password

    def _ssh_command(self, cmd):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.username, password=self.password, timeout=5)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            ssh.close()
            return output
        except Exception as e:
            print(f"SSH error {self.ip}: {e}")
            return ""

    def get_cpu_usage(self):
        output = self._ssh_command("top -bn1 | grep '%Cpu'")
        # 範例解析，根據系統可能要調整
        match = re.search(r'(\d+\.\d+)\s*id', output)
        if match:
            idle = float(match.group(1))
            usage = 100 - idle
            return usage
        return 0

    def get_memory_usage(self):
        output = self._ssh_command("free -m | grep Mem")
        parts = output.split()
        if len(parts) >= 7:
            total = int(parts[1]) * 1024 * 1024
            used = int(parts[2]) * 1024 * 1024
            percent = used / total * 100
            return {"total": total, "used": used, "percent": round(percent, 2)}
        return {"total": 0, "used": 0, "percent": 0}

    def get_disk_usage(self):
        output = self._ssh_command("df -h / | tail -1")
        parts = output.split()
        if len(parts) >= 5:
            total = parts[1]
            used = parts[2]
            percent_str = parts[4]
            percent = float(percent_str.strip('%'))
            return {"total": total, "used": used, "percent": percent}
        return {"total": "0", "used": "0", "percent": 0}

    def get_network_usage(self):
        output = self._ssh_command("cat /proc/net/dev | grep eth0")
        # 解析 eth0 的 bytes sent/recv
        if output:
            parts = output.split()
            if len(parts) >= 17:
                bytes_recv = int(parts[1])
                bytes_sent = int(parts[9])
                return {"bytes_sent": bytes_sent, "bytes_recv": bytes_recv}
        return {"bytes_sent": 0, "bytes_recv": 0}

    def get_all_status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "host": self.ip,
            "os": "linux",
            "cpu_percent": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "gpu": [],  # 你可以自行補充用 nvidia-smi 解析
            "network": self.get_network_usage()
        }
class MacOSMonitor:
    def __init__(self, ip, username=DEFAULT_LINUX_USER, password=DEFAULT_LINUX_PASS):
        self.ip = ip
        self.username = username
        self.password = password

    def _ssh_command(self, cmd):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username=self.username, password=self.password, timeout=5)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            ssh.close()
            return output
        except Exception as e:
            print(f"SSH error {self.ip}: {e}")
            return ""

    def get_cpu_usage(self):
        # 使用 top -l 1 -n 0 ，解析 CPU usage
        output = self._ssh_command("top -l 1 | grep 'CPU usage'")
        # 範例：CPU usage: 5.72% user, 9.18% sys, 85.08% idle
        match = re.search(r'(\d+\.\d+)% idle', output)
        if match:
            idle = float(match.group(1))
            return 100 - idle
        return 0

    def get_memory_usage(self):
        # 用 vm_stat 計算
        output = self._ssh_command("vm_stat")
        page_size = 4096  # bytes
        pages = {}
        for line in output.splitlines():
            parts = line.strip().split(':')
            if len(parts) == 2:
                key, val = parts
                pages[key] = int(val.strip().strip('.'))  # remove trailing .
        free = pages.get('Pages free', 0) * page_size
        active = pages.get('Pages active', 0) * page_size
        inactive = pages.get('Pages inactive', 0) * page_size
        wired = pages.get('Pages wired down', 0) * page_size
        speculative = pages.get('Pages speculative', 0) * page_size

        used = active + inactive + wired + speculative
        total = used + free
        percent = used / total * 100 if total else 0
        return {"total": total, "used": used, "percent": round(percent, 2)}

    def get_disk_usage(self):
        output = self._ssh_command("df -h / | tail -1")
        parts = output.split()
        if len(parts) >= 5:
            total = parts[1]
            used = parts[2]
            percent_str = parts[4]
            percent = float(percent_str.strip('%'))
            return {"total": total, "used": used, "percent": percent}
        return {"total": "0", "used": "0", "percent": 0}

    def get_network_usage(self):
        output = self._ssh_command("netstat -ib | grep en0")
        # 累計的 bytes recv / sent，取第一行 en0 的字串
        lines = output.strip().splitlines()
        if lines:
            parts = re.split(r'\s+', lines[0])
            try:
                bytes_recv = int(parts[6])
                bytes_sent = int(parts[9])
                return {"bytes_sent": bytes_sent, "bytes_recv": bytes_recv}
            except:
                pass
        return {"bytes_sent": 0, "bytes_recv": 0}

    def get_all_status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "host": self.ip,
            "os": "macos",
            "cpu_percent": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "gpu": [],
            "network": self.get_network_usage()
        }


# --- WinRM (Windows) 監控類別 ---
class WindowsMonitor:
    def __init__(self, ip, username='user', password='pass'):
        self.ip = ip
        self.username = username
        self.password = password
        self.session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))

    def run_cmd(self, cmd):
        try:
            r = self.session.run_cmd(cmd)
            return r.std_out.decode()
        except Exception as e:
            print(f"WinRM error {self.ip}: {e}")
            return ""

    def get_cpu_usage(self):
        output = self.run_cmd('wmic cpu get loadpercentage /value')
        match = re.search(r'LoadPercentage=(\d+)', output)
        if match:
            return float(match.group(1))
        return 0

    def get_memory_usage(self):
        output = self.run_cmd('wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value')
        free = total = 0
        for line in output.splitlines():
            if line.startswith('FreePhysicalMemory='):
                free = int(line.split('=')[1])
            elif line.startswith('TotalVisibleMemorySize='):
                total = int(line.split('=')[1])
        if total > 0:
            used = total - free
            percent = used / total * 100
            # 轉成 bytes
            return {"total": total * 1024, "used": used * 1024, "percent": round(percent, 2)}
        return {"total": 0, "used": 0, "percent": 0}

    def get_disk_usage(self):
        output = self.run_cmd('wmic logicaldisk get size,freespace,caption')
        lines = output.strip().splitlines()
        total = used = 0
        for line in lines[1:]:
            parts = line.split()
            if len(parts) == 3 and parts[0] == 'C:':
                free = int(parts[1])
                size = int(parts[2])
                used = size - free
                percent = used / size * 100
                return {"total": size, "used": used, "percent": round(percent, 2)}
        return {"total": 0, "used": 0, "percent": 0}

    def get_network_usage(self):
        # WinRM 用命令取得網路統計比較複雜，可以用 powershell 指令
        script = """
        $net = Get-NetAdapterStatistics | Select-Object -First 1
        Write-Output "$($net.ReceivedBytes),$($net.SentBytes)"
        """
        output = self.session.run_ps(script).std_out.decode().strip()
        if ',' in output:
            recv, sent = output.split(',')
            return {"bytes_recv": int(recv), "bytes_sent": int(sent)}
        return {"bytes_sent": 0, "bytes_recv": 0}

    def get_all_status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "host": self.ip,
            "os": "windows",
            "cpu_percent": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "gpu": [],  # Windows GPU 資料可用 wmi 或第三方工具，但較複雜
            "network": self.get_network_usage()
        }


# --- 管理器 ---
class MonitorManager:
    def __init__(self, hosts_config):
        self.hosts_config = hosts_config
        self.monitors = []

        # 預設帳密，你可以改成從 config 檔或 DB 讀取
        self.default_linux_user = 'your_linux_user'
        self.default_linux_pass = 'your_linux_password'
        self.default_windows_user = 'your_windows_user'
        self.default_windows_pass = 'your_windows_password'

        self._create_monitors()

    def _create_monitors(self):
        for key in self.hosts_config:
            val = self.hosts_config[key]
            ip, os_type = [v.strip().lower() for v in val.split(',')]
            if os_type == 'linux':
                self.monitors.append(LinuxMonitor(ip))
            elif os_type == 'windows':
                self.monitors.append(WindowsMonitor(ip))
            elif os_type == 'macos':
                self.monitors.append(MacOSMonitor(ip))
            else:
                print(f"Unknown OS type {os_type} for host {ip}")


    def get_all_status(self):
        results = []
        threads = []
        lock = threading.Lock()

        def fetch(monitor):
            status = monitor.get_all_status()
            with lock:
                results.append(status)

        for m in self.monitors:
            t = threading.Thread(target=fetch, args=(m,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        return results


monitor_manager = MonitorManager(hosts)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    data = monitor_manager.get_all_status()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
