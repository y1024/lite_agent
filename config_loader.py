# 根目录 config_loader.py (shim) — 显式列出全部公开 API, 防 __all__ 漏导出
from core.config_loader import (  # noqa: F401
    load_env, load_config, bust_base_cache,
    write_setting, write_conf_d, rollback_setting,
    SENSITIVE_SEGS,
)
