"""Short-term memory wrapper + compression."""
from __future__ import annotations
from ..core.context import SessionContext
from ..utils.logger import log


def compress_if_needed(ctx: SessionContext, util_pct: float, threshold: float = 85.0) -> bool:
    if util_pct < threshold or len(ctx.exchange_buffer) < 6:
        return False
    half = len(ctx.exchange_buffer) // 2
    old = ctx.exchange_buffer[:half]
    keep = ctx.exchange_buffer[half:]
    summary = "Summary of earlier exchanges: " + "; ".join(
        x["content"][:120].replace("\n", " ") for x in old
    )[:600]
    ctx.exchange_buffer = [{"role": "system", "content": summary}] + keep
    log(f"[MEMORY] Compressed {len(old)} exchanges (~{sum(len(x['content']) for x in old)} chars)")
    return True
