from openai import OpenAI
from typing import Optional


class ModelRouter:

    def __init__(self, config: dict):
        llm_cfg = config.get("llm", {})
        self.models_cfg: dict[str, dict] = llm_cfg.get("models", {})
        self.default_model = llm_cfg.get("default", "")
        routing = config.get("task_routing", {})
        self.rules: list[dict] = routing.get("route_rules", [])
        self._clients: dict[str, OpenAI] = {}
        self._init_clients()

    def _init_clients(self):
        for name, cfg in self.models_cfg.items():
            self._clients[name] = OpenAI(
                api_key=cfg["api_key"],
                base_url=cfg["base_url"],
            )

    def route(self, subtask_type: str) -> tuple[str, OpenAI, list[str]]:
        for rule in self.rules:
            if rule.get("type") == subtask_type:
                model_name = rule["model"]
                client = self._clients.get(model_name)
                tools = rule.get("tools", [])
                return (model_name, client, tools)
        default_client = self._clients.get(self.default_model)
        return (self.default_model, default_client, [])

    def get_fallback(self, model_name: str) -> Optional[tuple[str, OpenAI]]:
        for rule in self.rules:
            if rule.get("model") == model_name and rule.get("fallback"):
                fb_name = rule["fallback"]
                fb_client = self._clients.get(fb_name)
                if fb_client:
                    return (fb_name, fb_client)
        return None

    def get_client(self, model_name: str) -> Optional[OpenAI]:
        return self._clients.get(model_name)

    def supports_vision(self, model_name: str) -> bool:
        cfg = self.models_cfg.get(model_name, {})
        tags = cfg.get("tags", [])
        return "multimodal" in tags or "vision" in tags
