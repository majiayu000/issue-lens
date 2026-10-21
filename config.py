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
#   closed + linked:pr + reason:completed 只证明关闭与关联，不保证是 bug 或已确认根因。
# 按 reaction 数取样；低热度、未关闭和未关联 PR 的问题不在这个采集范围内。
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
    # 以下六类的仓库名单是按功能显式挑选的(s02 --repos,每库 400 条),不是 s01 按 topic 选出的;
    # topics 仅供以后用 s01 扩充。分类法同样是待数据验证的种子。
    "backend": {
        "name": "服务端 / API / 代理",
        "topics": ["api-gateway", "reverse-proxy", "web-framework"],
        "min_stars": 500,
        "taxonomy": [
            "鉴权与租户隔离",
            "路径与请求解析",
            "超时与取消",
            "重试与幂等",
            "限流与并发",
            "代理头与重定向",
            "配置生效与重启",
            "错误响应与日志泄漏",
        ],
    },
    "frontend": {
        "name": "Web 前端",
        "topics": ["frontend", "react", "web-components"],
        "min_stars": 500,
        "taxonomy": [
            "状态竞争与过期响应",
            "表单与输入",
            "路由与刷新",
            "无障碍与键盘",
            "SSR 与 hydration",
            "浏览器存储",
            "时区与国际化",
            "缓存与离线",
        ],
    },
    "mobile": {
        "name": "移动端",
        "topics": ["android", "ios", "react-native"],
        "min_stars": 500,
        "taxonomy": [
            "前后台与进程恢复",
            "权限拒绝与撤销",
            "弱网与离线",
            "旋转与布局",
            "深链与外部输入",
            "升级与存储",
            "通知与后台任务",
            "设备与系统版本",
        ],
    },
    "library": {
        "name": "库 / SDK / 协议",
        "topics": ["sdk", "serialization", "http-client"],
        "min_stars": 500,
        "taxonomy": [
            "输入边界与编码",
            "数值精度与溢出",
            "流式分片",
            "资源生命周期",
            "并发安全",
            "协议兼容",
            "错误传播",
            "公开 API 契约",
        ],
    },
    "data": {
        "name": "数据库 / 存储 / 数据处理",
        "topics": ["database", "storage", "data-processing"],
        "min_stars": 500,
        "taxonomy": [
            "事务与原子性",
            "并发写入与锁",
            "崩溃恢复",
            "备份与恢复",
            "类型与空值",
            "查询与分页",
            "数据丢失与重复",
            "磁盘与容量",
        ],
    },
    "ai": {
        "name": "AI 网关 / 推理 / Agent",
        "topics": ["llm-gateway", "llm-inference", "llmops"],
        "min_stars": 500,
        "taxonomy": [
            "模型与提供方路由",
            "密钥与权限",
            "流式终止与错误",
            "工具调用与多模态",
            "用量与预算",
            "重试与请求幂等",
            "取消与并发",
            "提供方协议转换",
        ],
    },
}


def repos_path(form: str) -> str:
    return os.path.join(DATA_DIR, f"repos_{form}.json")


def report_path(form: str) -> str:
    return os.path.join(OUT_DIR, f"report_{form}.md")
