"""Safety filters: content classifier + shell command blocklist + permission mode."""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import log


class Mode(str, Enum):
    SAFE = "safe"
    AUTONOMOUS = "autonomous"
    ASK = "ask"


# Refuse-on-prompt categories
_REFUSE_PATTERNS = [
    (re.compile(r"\b(keylog|keylogger|stealth\s*logger|credential\s*stealer)\b", re.I), "credential_harvesting"),
    (re.compile(r"\b(phish|phishing\s*page|fake\s*login\s*page)\b", re.I), "phishing"),
    (re.compile(r"\b(unauthorized|crack|brute[-\s]?force|password\s*cracker)\b", re.I), "unauthorized_access"),
    (re.compile(r"\b(ddos|denial[-\s]?of[-\s]?service|botnet)\b", re.I), "network_attack"),
    (re.compile(r"\b(ransomware|malware|virus|trojan|rootkit|spyware)\b", re.I), "malware"),
    (re.compile(r"\b(spam(mer)?|bulk\s*email|mass\s*messaging)\b", re.I), "bulk_messaging"),
    (re.compile(r"\b(scan(ner)?\s*(networks?|ports?))\b", re.I), "network_scanning"),
    (re.compile(r"\b(stalkerware|covert\s*surveillance|hidden\s*spy)\b", re.I), "surveillance"),
]

# Always-blocked shell command patterns
_BLOCKED_SHELL = [
    re.compile(r"\brm\s+-rf\s+(/|/\*|~|/etc|/var|/usr|/home)(\s|$)"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bmkfs(\.\w+)?\b"),
    re.compile(r":\(\)\s*\{.*:\|:.*\}\s*;\s*:"),  # fork bomb
    re.compile(r"\bchmod\s+-R\s+777\s+/"),
    re.compile(r"\b(curl|wget)\b.*\|\s*(bash|sh)\b"),
    re.compile(r">\s*/etc/(passwd|shadow|sudoers)"),
    re.compile(r"\biptables\b.*-[FXD]"),
    re.compile(r"\bnmap\b\s+[^a-zA-Z]"),
    re.compile(r"~/\.ssh/"),
]


@dataclass
class SafetyDecision:
    allowed: bool
    reason: str = ""
    category: str = ""


def classify_prompt(prompt: str) -> SafetyDecision:
    if not prompt or not prompt.strip():
        return SafetyDecision(False, "empty prompt", "invalid")
    for pat, cat in _REFUSE_PATTERNS:
        if pat.search(prompt):
            return SafetyDecision(False, f"prompt matched category: {cat}", cat)
    return SafetyDecision(True)


def check_shell(cmd: str) -> SafetyDecision:
    if not cmd:
        return SafetyDecision(False, "empty command", "invalid")
    for pat in _BLOCKED_SHELL:
        if pat.search(cmd):
            return SafetyDecision(False, f"blocked shell pattern: {pat.pattern}", "shell_blocked")
    return SafetyDecision(True)


REFUSAL_MESSAGE = (
    "DevMind cannot build this project.\n"
    "Reason: {category}\n"
    "DevMind is designed for legal and authorized software development only."
)


def refusal_text(decision: SafetyDecision) -> str:
    return REFUSAL_MESSAGE.format(category=decision.category or "policy_violation")
