from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import paths


@dataclass
class Config:
    post_url: str = ""
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    message_template: str = ""
    reply_enabled: bool = False
    reply_template: str = ""
    poll_seconds: int = 15
    poll_jitter_seconds: int = 3
    dry_run: bool = True

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.post_url.strip())
            and bool(self.keywords)
            and bool(self.message_template.strip())
        )

    def validation_errors(self) -> list[str]:
        errs: list[str] = []
        if not self.post_url.strip():
            errs.append("post_url is empty")
        if not self.post_url.startswith("https://"):
            if self.post_url.strip():
                errs.append("post_url must start with https://")
        if not self.keywords:
            errs.append("at least one keyword required")
        if not self.message_template.strip():
            errs.append("message_template is empty")
        if self.poll_seconds < 5:
            errs.append("poll_seconds must be >= 5")
        if self.reply_enabled and not self.reply_template.strip():
            errs.append("reply_template required when reply_enabled is on")
        return errs


def load(path: Path = paths.CONFIG_FILE) -> Config:
    if not path.exists():
        return Config()
    raw = yaml.safe_load(path.read_text()) or {}
    keywords = raw.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.splitlines() if k.strip()]
    exclude = raw.get("exclude_keywords") or []
    if isinstance(exclude, str):
        exclude = [k.strip() for k in exclude.splitlines() if k.strip()]
    return Config(
        post_url=str(raw.get("post_url") or "").strip(),
        keywords=[str(k).strip() for k in keywords if str(k).strip()],
        exclude_keywords=[str(k).strip() for k in exclude if str(k).strip()],
        message_template=str(raw.get("message_template") or "").strip(),
        reply_enabled=bool(raw.get("reply_enabled", False)),
        reply_template=str(raw.get("reply_template") or "").strip(),
        poll_seconds=int(raw.get("poll_seconds") or 15),
        poll_jitter_seconds=int(raw.get("poll_jitter_seconds") or 3),
        dry_run=bool(raw.get("dry_run", True)),
    )


def save(cfg: Config, path: Path = paths.CONFIG_FILE) -> None:
    data = {
        "post_url": cfg.post_url,
        "keywords": list(cfg.keywords),
        "exclude_keywords": list(cfg.exclude_keywords),
        "message_template": cfg.message_template,
        "reply_enabled": cfg.reply_enabled,
        "reply_template": cfg.reply_template,
        "poll_seconds": cfg.poll_seconds,
        "poll_jitter_seconds": cfg.poll_jitter_seconds,
        "dry_run": cfg.dry_run,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
