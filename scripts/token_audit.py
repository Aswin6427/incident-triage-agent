"""Token audit: before vs after optimization across all agents."""
import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("PYTHONPATH", ".")

import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")

from backend.agents.log_analyzer import _trim_logs, SYSTEM_PROMPT as SYS_LOG
from backend.agents.past_ticket  import _slim_ticket, SYSTEM_PROMPT as SYS_TICKET
from backend.agents.runbook      import SYSTEM_PROMPT as SYS_RUNBOOK
from backend.agents.root_cause   import SYSTEM_PROMPT as SYS_ROOT
from backend.agents.post_mortem  import SYSTEM_PROMPT as SYS_PM
from backend.mcp.gateway import MCPGateway

BEFORE = {
    "LogAnalyzerAgent":  (186, 1500),
    "PastTicketAgent":   (197, 2500),
    "RunbookAgent":      (130, 1500),
    "RootCauseAgent":    (379, 3000),
    "PostMortemAgent":   (206, 2500),
}

after_agents = [
    ("LogAnalyzerAgent",  SYS_LOG,     1000),
    ("PastTicketAgent",   SYS_TICKET,  1500),
    ("RunbookAgent",      SYS_RUNBOOK, 1000),
    ("RootCauseAgent",    SYS_ROOT,    2000),
    ("PostMortemAgent",   SYS_PM,      2000),
]


async def main():
    sep = "-" * 78
    hdr = f"  {'Agent':<22} {'SYS before':>10} {'SYS after':>10} {'Saved':>8}  {'Out before':>10} {'Out after':>9}"
    print("\n" + hdr)
    print("  " + sep)

    total_saved_sys = 0
    total_saved_out = 0
    for name, prompt, new_max in after_agents:
        b_sys, b_out = BEFORE[name]
        a_sys = len(enc.encode(prompt))
        saved_sys = b_sys - a_sys
        saved_out = b_out - new_max
        total_saved_sys += saved_sys
        total_saved_out += saved_out
        print(f"  {name:<22} {b_sys:>10} {a_sys:>10} {saved_sys:>+8}  {b_out:>10} {new_max:>9}")

    total_b = sum(b for b, _ in BEFORE.values())
    total_a = sum(len(enc.encode(p)) for _, p, _ in after_agents)
    print("  " + sep)
    print(f"  {'TOTAL':<22} {total_b:>10} {total_a:>10} {total_saved_sys:>+8}")

    # Measure live log payload reduction
    mcp  = MCPGateway()
    logs = await mcp.call_tool(
        "search_logs",
        {"service": "payment-service", "timestamp": "2026-06-05T10:00:00Z", "window_minutes": 30},
    )
    before_t = len(enc.encode(json.dumps(logs)))
    trimmed  = _trim_logs(logs)
    after_t  = len(enc.encode(json.dumps(trimmed)))
    log_saved = before_t - after_t

    print(f"\n  Log payload    : {len(logs)} entries  ->  {len(trimmed)} entries  (-{len(logs)-len(trimmed)})")
    print(f"  Log tokens     : {before_t}  ->  {after_t}  (saved {log_saved}, {log_saved/before_t*100:.0f}% reduction)")

    total_per = total_saved_sys + log_saved
    print("\n  TOTAL SAVINGS PER INCIDENT TRIAGE")
    print("  " + sep)
    print(f"  System prompts  : -{total_saved_sys} tokens")
    print(f"  Log payload     : -{log_saved} tokens")
    print(f"  Max output cap  : -{total_saved_out} tokens")
    print("  " + sep)
    print(f"  Per incident    : ~-{total_per} input tokens")
    print(f"  x 5 incidents   : ~-{total_per * 5} input tokens per full run")
    print()


if __name__ == "__main__":
    asyncio.run(main())
