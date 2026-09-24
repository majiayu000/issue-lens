"""集中配置:形态定义、初始分类法、规模参数。

路径与规模参数可被环境变量覆盖:
  ISSUE_LENS_DB          SQLite 路径(默认 data/issues.db)
  ISSUE_LENS_MAX_REPOS   每形态抓取仓库数上限(默认 40)
  ISSUE_LENS_MAX_ISSUES  每仓库抓取 issue 数上限(默认 1000)
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
OUT_DIR = os.path.join(BASE, "out")
DB_PATH = os.environ.get("ISSUE_LENS_DB", os.path.join(DATA_DIR, "issues.db"))

MAX_REPOS = int(os.environ.get("ISSUE_LENS_MAX_REPOS", "40"))
MAX_ISSUES = int(os.environ.get("ISSUE_LENS_MAX_ISSUES", "1000"))

# 质量过滤定义(与调研报告一致):
#   closed + linked:pr(与修复 PR 关联)+ reason:completed(维护者确认为已解决的真实问题)
# 按reaction数降序取前 N 条——我们要的是"被最多人验证过的真问题"。
ISSUE_QUERY = "is:issue is:closed linked:pr reason:completed"

FORMS = {
    "desktop": {
        "name": "桌面 App",
        "topics": ["electron", "tauri", "desktop-app"],
        "min_stars": 500,
        # 初始分类法:桌面形态缺系统研究,以下为待数据验证的种子(见调研报告 §5)
        "taxonomy": [
            "崩溃与启动失败",
            "安装与升级",
            "自动更新",
            "渲染与 UI 布局",
            "文件关联/拖拽/外部协议",
            "权限与沙箱(摄像头/麦克风/通知/辅助功能)",
            "快捷键与输入法",
            "窗口管理(多窗口/托盘/全屏)",
            "性能与内存占用",
            "平台差异(macOS/Windows/Linux)",
            "国际化/时区/编码",
            "数据迁移与旧版本兼容",
        ],
    },
    "cli": {
        "name": "CLI / 终端工具",
        "topics": ["cli", "command-line", "terminal"],
        "min_stars": 1000,
        # 初始分类法:配置错误为首位(Yin SOSP 2011:占真实配置故障 70–85%)
        "taxonomy": [
            "配置错误",
            "参数解析与默认值",
            "退出码与错误输出",
            "编码与终端兼容(颜色/宽度/Unicode)",
            "管道与重定向",
            "安装与依赖(二进制/包管理器)",
            "文件系统与权限",
            "性能与大数据量",
            "跨平台差异",
            "版本升级与配置迁移",
        ],
    },
}


def repos_path(form: str) -> str:
    return os.path.join(DATA_DIR, f"repos_{form}.json")


def report_path(form: str) -> str:
    return os.path.join(OUT_DIR, f"report_{form}.md")
