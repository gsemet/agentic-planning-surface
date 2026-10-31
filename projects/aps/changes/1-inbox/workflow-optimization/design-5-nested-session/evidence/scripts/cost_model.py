# /// script
# requires-python = ">=3.11"
# ///
"""Orchestration cost per CR and per week: design 5 on Claude Desktop (as tested, optimized)
against design 1's dynamic workflow. Every figure is a (low, high) pair.

Prices $/MTok (design 2, prices-corrected.md): Opus 4 / 8 (1-h write) / 0.20 (read) / 20 (out),
Sonnet half of Opus. Volume: about 94 CRs a week (design 1, section 12).
Workers (Coder, Inspector) are the same in both designs and are left out, except the extra
rounds the dynamic workflow causes.

Usage: python3 cost_model.py
"""

CRS_PER_WEEK = 94
OPUS = {"w1h": 8, "read": 0.20, "out": 20}
SONNET = {k: v / 2 for k, v in OPUS.items()}


def call(model: dict, context: float, written: float, out: float) -> float:
    """Cost of one model call with a warm one-hour cache."""
    return (context * model["read"] + written * model["w1h"] + out * model["out"]) / 1e6


def span(f, lo: dict, hi: dict) -> tuple[float, float]:
    return f(**lo), f(**hi)


def mul(a, b):
    return a[0] * b[0], a[1] * b[1]


def add(*xs):
    return sum(x[0] for x in xs), sum(x[1] for x in xs)


# ---- design 5, optimized ----------------------------------------------------------------
# Foreman on Sonnet, low effort, detached; one `crf event` call per Driver event.
# Context 70k (Desktop prefix, measured) to 110k (compaction at 100k plus the turn).
fm_call = (call(SONNET, 70e3, 500, 280), call(SONNET, 110e3, 1200, 280))
fm_events_per_cr = (5, 8)  # spawn share, PR opened, CI result, hand-back, 1 wait notice, orders
fm_calls_per_event = (1.2, 2.0)
foreman = mul(mul(fm_call, fm_calls_per_event), fm_events_per_cr)
# Batch start: the 70k prefix written once at the one-hour price; 15-25 batches a week.
foreman_start_week = (15 * 70e3 * SONNET["w1h"] / 1e6, 25 * 70e3 * SONNET["w1h"] / 1e6)
# Heartbeat: one call per active batch hour, 30-60 hours a week.
ticks_week = (30 * fm_call[0], 60 * fm_call[1])

# Driver: Sonnet, agent file prefix 17-20k (measured), 8-10 turns per CR with crf (design 2).
drv_turn = (call(SONNET, 25e3, 1000, 400), call(SONNET, 45e3, 3000, 800))
driver = add(mul(drv_turn, (8, 10)), (18e3 * SONNET["w1h"] / 1e6, 20e3 * SONNET["w1h"] / 1e6))
# Stack driver: design 2 after levers, $3.4-8.9 a week.
stack = (3.4 / CRS_PER_WEEK, 8.9 / CRS_PER_WEEK)
# Chief of Staff: 1-2 Foreman messages per CR, $0.05-0.10 each (measured $0.069 at 108k).
cos = mul((1, 2), (0.05, 0.10))

d5_opt = add(foreman, driver, stack, cos)

# ---- design 5, lean events -------------------------------------------------------------------
# Drivers write routine milestones (PR opened, CI green) with `crf report`; they message the
# Foreman only for a hand-back, a question or an anomaly. The heartbeat reads `crf status`.
lean_events_per_cr = (2, 3)
foreman_lean = mul(mul(fm_call, fm_calls_per_event), lean_events_per_cr)
cos_lean = mul((0.7, 1.2), (0.05, 0.10))  # PR links batched per stack
d5_lean = add(foreman_lean, driver, stack, cos_lean)

# ---- design 5, as tested -----------------------------------------------------------------
# Opus Foreman, attached, measured $0.09-0.20 per Driver event in sim-1 and sim-2.
foreman_tested = mul((0.09, 0.20), fm_events_per_cr)
notes = mul((0.030, 0.050), fm_events_per_cr)  # one app note per Foreman turn
d5_tested = add(foreman_tested, notes, driver, stack, cos)
tested_start_week = (15 * 70e3 * OPUS["w1h"] / 1e6, 25 * 70e3 * OPUS["w1h"] / 1e6)

# ---- design 1, dynamic workflow -----------------------------------------------------------
runners = mul((8, 10), (0.005, 0.01))  # Haiku agents that run crf
judge = (60 * 0.20 / CRS_PER_WEEK, 150 * 0.50 / CRS_PER_WEEK)  # 60-150 events a week, $0.20-0.50
cos_wf = (3 / CRS_PER_WEEK, 10 / CRS_PER_WEEK)
extra_rounds = (5 / CRS_PER_WEEK, 43 / CRS_PER_WEEK)
wf = add(runners, judge, cos_wf, extra_rounds)


def row(name, per_cr, week_extra=(0, 0)):
    wk = (per_cr[0] * CRS_PER_WEEK + week_extra[0], per_cr[1] * CRS_PER_WEEK + week_extra[1])
    print(f"| {name} | ${per_cr[0]:.2f}–{per_cr[1]:.2f} | ${wk[0]:.0f}–{wk[1]:.0f} |")


print("| Part | Per CR | Per week |")
print("| --- | ---: | ---: |")
print("| **Design 5, optimized** | | |")
row("Foreman events", foreman)
row("Foreman starts and ticks", (0, 0), add(foreman_start_week, ticks_week))
row("Drivers", driver)
row("Stack driver", stack)
row("Chief of Staff", cos)
row("**Total**", d5_opt, add(foreman_start_week, ticks_week))
print("| **Design 5, lean events** | | |")
row("Foreman events", foreman_lean)
row("Chief of Staff", cos_lean)
row("**Total**", d5_lean, add(foreman_start_week, ticks_week))
print("| **Design 5, as tested** | | |")
row("Foreman events (Opus)", foreman_tested)
row("App notes to the Chief of Staff", notes)
row("**Total**", d5_tested, add(tested_start_week, ticks_week))
print("| **Dynamic workflow** | | |")
row("crf runners (Haiku)", runners)
row("Judge", judge)
row("Chief of Staff", cos_wf)
row("Extra Coder rounds", extra_rounds)
row("**Total**", wf)
print(f"\nper-call Sonnet Foreman ${fm_call[0]:.4f}-{fm_call[1]:.4f}; Driver turn "
      f"${drv_turn[0]:.4f}-{drv_turn[1]:.4f}")
