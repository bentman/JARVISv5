# 🤖 J.A.R.V.I.S v5

[![Not Real Magic](https://img.shields.io/badge/ai-Not_Real_Magic-purple)](#)
[![Stability: Mostly](https://img.shields.io/badge/stability-Mostly-yellow)](#)
[![Status: Evolving](https://img.shields.io/badge/status-Actively_Evolving-green)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🪄 **J**ust **A** **R**ewrite, **V**erging **I**nto **S**orcery - Mark5

- Still not sentient. 
- Still not flying the suit.
- But slightly more than just a chatbot duct-taped to a system utility.

JARVISv5 is the latest incarnation of a system that has been rewritten more times than a tax code loophole. It’s now a modular, agent‑ready, locally‑runnable, “please‑don’t-break-this-time” architecture built around clean phases, explicit approvals, and the ongoing dream that one day it will behave predictably. This version is the first to have an actual system inventory, real workflow boundaries, and fewer “accidental features” than previous releases. It’s still not a magical AI but it is finally organized enough that future‑me won’t file a missing‑person report on past‑me.

> _A personal project that keeps getting rebuilt because apparently that’s my hobby now._

---

## 🔮 Project Vision (“Trying very hard not to reinvent itself again”)

JARVISv5 is trying very hard to be a daily‑use personal assistant instead of a chaotic gremlin with root access. It aims for a world where tasks run locally, decisions follow actual rules, and every action leaves behind enough artifacts that future‑you can audit past‑you without needing therapy. It’s privacy‑aware, reproducible, and only escalates to the cloud when absolutely necessary—or when you explicitly allow it to misbehave.

### Core Invariants

- **Local‑First Execution** — If your machine can handle it, your machine will handle it. Cloud calls require emotional justification and a signed permission slip.
- **Deterministic Control** — A state machine is in charge because letting the LLM “drive” is how you end up with philosophical essays instead of working code.
- **Externalized Memory** — Nothing lives in the model’s imagination. If it matters, it’s written down somewhere you can grep later.
- **Traceability** — Every action produces artifacts, logs, receipts, and probably a confession. If something goes wrong, you’ll know exactly which component to blame.
- **Policy‑Bound Escalation** — Cloud usage is deliberate, budgeted, and guilt‑inducing by design. If JARVISv5 goes online, it’s because you told it to — not because it got curious.

> _**[Project.md](Project.md)** contains the actual vision. This README contains only the excuses._

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

> _To see what is (somewhat) verified to be (probably) working, see **[SYSTEM_INVENTORY.md](SYSTEM_INVENTORY.md)**_

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

> _“Building with high ambitions, grounded in (and by the) truth”_

---

## 🤝 Contributions Welcome!

A project this frequently rewritten practically requires outside help. Whether you’re adding workflow templates, fixing hardware detection, or gently suggesting that the UI deserves better, contributions are welcome and encouraged.

> _Standards, guardrails, and “please don’t break our universe” rules here: **[AGENTS.md](AGENTS.md)**_

---

## 📜 License

Distributed under the MIT License, which is basically the “do whatever you want, just don’t blame me when it breaks” license.

> _Standard yada-yada lives here: **[LICENSE](LICENSE)**_

---

## 🌟 Acknowledgments

This work builds upon the foundations (and failures) in:

- **[JARVISv1 (Just A Rough Very Incomplete Start)](https://github.com/bentman/JARVISv1)**
  - _The “learning to walk by falling down stairs” era._
- **[JARVISv2 (Just Almost Real Viable Intelligent System)](https://github.com/bentman/JARVISv2)**
  - _The version that felt promising right up until it wasn’t._
- **[JARVISv3 (Just A Reliable Variant In Service)](https://github.com/bentman/JARVISv3)**
  - _The first time things stopped catching fire long enough to be usable._
- **[JARVISv4 (Just A Reimagined Version In Stasis)](https://github.com/bentman/JARVISv4)**
  - _A bold redesign that immediately froze like a Windows 98 demo machine._

> _"Sometimes you gotta run before you can walk." - Tony Stark_
