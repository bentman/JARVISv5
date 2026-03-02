# J.A.R.V.I.S v5
## Just A Rewrite, Verging Into Sorcery - Mark5

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-Active-green)](#)

> Still not sentient. Still not flying the suit.
> But no longer just a chatbot duct-taped to a shell script.

*A personal project that keeps getting rebuilt because apparently that’s my hobby now.*

JARVISv5 is the latest incarnation of a system that has been rewritten more times than a tax code loophole. It’s now a modular, agent‑ready, locally‑runnable, “please‑don’t-break-this-time” architecture built around clean phases, explicit approvals, and the ongoing dream that one day it will behave predictably.

This version is the first to have an actual system inventory, real workflow boundaries, and fewer “accidental features” than previous releases. It’s still not a magical AI but it is finally organized enough that future‑me won’t file a missing‑person report on past‑me.

---

## 🎯 Why v5 Exists
Because v4 taught me exactly one thing:  
- *“I can fix this… but only if I start over again.”*

---

## 🏗️ What This Is
JARVIS v5 is an evolving agentic runtime that can:
- recover from failure (sometimes)
- a system that is becoming less of a fire hazard
- plan, execute, validate, remember, and a few other tricks, too

All running locally in a structured, containerized environment designed to move from:
- *from toy AI demo → to actual task-capable system*

It’s an experiment in:
- *What happens when you stop asking LLMs questions and start giving them responsibility?*

## ⚠️ What This Isn’t
- finished, functional, reliable  
- a benchmark of anything except persistence  

## 🤖 Current Capability (Brutally Honest)
👍 JARVIS can:
- persist memory
- maintain task state
- execute multi-step flows
- reason across prior context
- recover from partial failures
- run repeatable validation harnesses

👎 JARVIS cannot:
- replace you (yet — relax)
- fully self-direct long horizon goals
- reliably use tools without guardrails
- improve itself without human scaffolding
- operate unsupervised without eventually doing something dumb

🔮 JARVIS Plans for the future:
- Add features that don’t immediately collapse  
- Reduce the number of rewrites per version  
- Eventually become a usable system  

---

What Exists Today
🧠 The Brain
Finite-state execution loop:
INIT → PLAN → EXECUTE → VALIDATE → COMMIT → ARCHIVE
Which means:
It doesn’t just respond — it finishes things.

📖 Memory
JARVIS remembers across:
working state
episodic traces
semantic storage
So conversations don’t reset into amnesia every 5 minutes anymore.

🛠️ Hardware Awareness
Detects system capability and adjusts model strategy.
Translation:
It tries not to melt your GPU unless necessary.

🏗️ Infrastructure
Runs inside a fully reproducible Docker environment with:
health checks
validation harness
model auto-download
inference normalization
failure visibility
Less “AI magic”.
More “observable system”.

Reality Check
This is not daily-driver autonomous AI.

It is:
stable enough to iterate
structured enough to grow
honest enough to expose its own limits

Progress now comes from:
Capability → Measurement → Correction
Not vibes.

Direction
The focus is shifting from:
“Can it respond intelligently?”
to
“Can it act reliably?”
That’s a much harder problem.

Status
Some days it feels like:
Early operating system for cognition.
Other days:
Fancy loop that occasionally surprises us.
Both are true.

Bottom Line
JARVIS v5 is no longer a demo.
It’s a system under construction.
And construction has finally replaced improvisation.

---
### Prerequisites

- **Docker** & **Docker Compose**
- **??? CPU** (full gpu reccommended, npu still needs work)
- **8GB+ RAM** (you will want much more)
- **5GB disk space** (you will need much more)
- 

---

## 🤝 Contributions Welcome!
Whether it's adding new workflow templates, improving hardware detection, or refining the UI, contributions are welcome. See our **[Agent Guidelines](AGENTS.md)** for standards.

---

## 📜 License
Distributed under the **MIT License**. See **[LICENSE](LICENSE)** for more information.

---

## 🌟 Acknowledgments
This work builds upon the foundations (and failures) in:
- [JARVISv1 (Just A Rough Very Incomplete Start)](https://github.com/bentman/JARVISv1)
- [JARVISv2 (Just Almost Real Viable Intelligent System)](https://github.com/bentman/JARVISv2) 
- [JARVISv3 (Just A Reliable Variant In Service)](https://github.com/bentman/JARVISv3)
- [JARVISv4 (Just A Reimagined Version In Stasis)](https://github.com/bentman/JARVISv4)

---

*"Sometimes you gotta run before you can walk." - Tony Stark*