"""LLM 提炼接口(本轮按约定未接引擎,只定义契约)。

输出契约(每条 issue 提炼为一个 JSON 对象):
  {
    "symptom":             "用户可见症状,一句话",
    "root_cause_category": "必须取自 config.FORMS[form]['taxonomy'] 之一",
    "environment":         ["受影响的平台/版本/权限/输入等环境因素"],
    "test_ideas":          ["可执行的测试点,每条一句祈使句"]
  }

接入新引擎:
  1. 设置环境变量 ISSUE_LENS_LLM_ENGINE=anthropic|deepseek(凭据继续走各自的环境变量,
     严禁写入代码、日志或提交);
  2. 在 _ENGINE_TABLE 注册实现,函数签名 (issue: dict, form: str) -> dict。
"""
import os

_ENGINE_TABLE: dict = {}


def extract_issue(issue: dict, form: str) -> dict | None:
    """提炼单条 issue。返回 None 表示"引擎未配置,只存原始 issue"。"""
    engine = os.environ.get("ISSUE_LENS_LLM_ENGINE", "none")
    if engine == "none":
        return None
    fn = _ENGINE_TABLE.get(engine)
    if fn is None:
        raise ValueError(
            f"未知提炼引擎: {engine}(已注册: {sorted(_ENGINE_TABLE) or '无'};"
            f"支持 anthropic/deepseek,接入方式见本模块 docstring)")
    return fn(issue, form)
