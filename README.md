# 🤖 J.A.R.V.I.S v5
## Just A Rewrite, Verging Into Sorcery - Mark5

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-Active-green)](#)

> Still not sentient. Still not flying the suit.
> But no longer just a chatbot duct-taped to a shell script.

*A personal project that keeps getting rebuilt because apparently that’s my hobby now.*

JARVISv5 is the latest incarnation of a system that has been rewritten more times than a tax code loophole. It’s now a modular, agent‑ready, locally‑runnable, “please‑don’t-break-this-time” architecture built around clean phases, explicit approvals, and the ongoing dream that one day it will behave predictably.

This version is the first to have an actual system inventory, real workflow boundaries, and fewer “accidental features” than previous releases. It’s still not a magical AI but it is finally organized enough that future‑me won’t file a missing‑person report on past‑me.

---

## 👁️ Project Vision (“Trying very hard not to reinvent itself again”)

JARVISv5 is trying very hard to be a daily‑use personal assistant instead of a chaotic gremlin with root access. It aims for a world where tasks run locally, decisions follow actual rules, and every action leaves behind enough artifacts that future‑you can audit past‑you without needing therapy. It’s privacy‑aware, reproducible, and only escalates to the cloud when absolutely necessary—or when you explicitly allow it to misbehave.

### Core Invariants
- **Local‑First Execution** — If your machine can handle it, your machine will handle it. Cloud calls require emotional justification and a signed permission slip.
- **Deterministic Control** — A state machine is in charge because letting the LLM “drive” is how you end up with philosophical essays instead of working code.
- **Externalized Memory** — Nothing lives in the model’s imagination. If it matters, it’s written down somewhere you can grep later.
- **Traceability** — Every action produces artifacts, logs, receipts, and probably a confession. If something goes wrong, you’ll know exactly which component to blame.
- **Policy‑Bound Escalation** — Cloud usage is deliberate, budgeted, and guilt‑inducing by design. If JARVISv5 goes online, it’s because you told it to — not because it got curious.

---

## 🧱 What This Is ("This is a structure, not a miracle")

JARVISv5 is an agentic runtime that has finally stopped pretending to be a mystical AI and now behaves like a slightly over‑engineered appliance with opinions. It’s built to run workflows without wandering off, forget what it was doing, or reinvent your directory structure out of boredom. It’s structured, deterministic, and just self‑aware enough to know it needs guardrails.

### Capabilities (in their brutally honest form)
- **Persist memory** — Not “AI memory,” but actual files, because trusting an LLM to remember things is how disasters happen.
- **Maintain task state** — Keeps transcripts short enough to avoid amnesia but long enough to remember why it walked into the room.
- **Execute multi‑step flows** — Uses a deterministic FSM/DAG so the runtime can’t improvise its way into a new religion.
- **Reason across prior context** — Hybrid semantic retrieval that works better than vibes but worse than a human with coffee.
- **Recover from partial failures** — Validation gates that prevent the system from confidently marching into a mistake.
- **Run repeatable validation harnesses** — Deterministic replay so you can prove it was the machine’s fault, not yours.

All running locally in a structured, containerized environment designed to move from:
- *toy AI demo → actual task-capable system*

It’s an experiment in:
- *What happens when you stop asking LLMs questions and start giving them responsibility?*

---

## 🚫 What This Isn’t (Yet)
JARVISv5 is many things, but it is not a fully autonomous, self‑correcting, omniscient digital butler. It’s more like a very organized intern who follows instructions, documents everything, and occasionally forgets what it was doing but at least leaves a paper trail. These are the things it absolutely does not claim to be—yet.

### Limits, stated plainly
- **Not magic** — No genius, no revelations, no miracles — just workflows doing their job.
- **Not a general AI** — It’s a runtime with guardrails, not a consciousness with ambition.
- **Not a mind-reader** — If you don’t specify it, it doesn’t assume it. That’s how v4 died.
- **Not a stable API** — The architecture changes whenever you get a new idea in the shower.
- **Not autonomous** — It will not run off and “handle things” for you. It barely trusts itself.
- **Not finished** — It’s v5, which implies four previous attempts and at least six future ones.

“Functional, structured, and mostly aware of its own limitations.”

---

## 🤝 Contributions Welcome!

🤝 Contributions Welcome!
A project this frequently rewritten practically requires outside help. Whether you’re adding workflow templates, fixing hardware detection, or gently suggesting that the UI deserves better, contributions are welcome and encouraged. 
> Standards, guardrails, and “please don’t break our universe” rules live in
**[AGENTS.md](AGENTS.md)**.

---

## 📜 License

Distributed under the MIT License, which is basically the “do whatever you want, just don’t blame me when it breaks” license. 
> Full text lives in **[LICENSE](LICENSE)**.

---

## 🌟 Acknowledgments

This work builds upon the foundations (and failures) in:
- [JARVISv1 (Just A Rough Very Incomplete Start)](https://github.com/bentman/JARVISv1)
  - *The “learning to walk by falling down stairs” era.*
- [JARVISv2 (Just Almost Real Viable Intelligent System)](https://github.com/bentman/JARVISv2)
  - *The version that felt promising right up until it wasn’t.*
- [JARVISv3 (Just A Reliable Variant In Service)](https://github.com/bentman/JARVISv3)
  - *The first time things stopped catching fire long enough to be usable.*
- [JARVISv4 (Just A Reimagined Version In Stasis)](https://github.com/bentman/JARVISv4)
  - *A bold redesign that immediately froze like a Windows 98 demo machine.*

---

## *"Sometimes you gotta run before you can walk." - Tony Stark*