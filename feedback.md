# Interview Feedback — AI Coding Interview (Big Tech Bar)

**Scope:** Prompting, Research, and Planning only. Code walkthrough excluded.

---

## Ratings

| Area | Score |
|---|---|
| Research & Framing | 7 / 10 |
| Prompting & Communication | 8.5 / 10 |
| Planning & Decomposition | 8 / 10 |
| **Overall** | **7.8 / 10** |

**Verdict: Lean Hire**

---

## Detailed Breakdown

### Research & Problem Framing — 7 / 10

**Strengths:**
- Structured the Research.md proactively with an `## Important` meta-section that explicitly told the collaborator how to interact (justify with pros/cons). That's a senior-level habit — setting ground rules before work begins.
- Correctly identified the tradeoff axes (algorithm choice, storage backend, library vs. manual) and organized them independently. Shows systems thinking.
- Anticipated future scale requirements (100 req/min, 1k req/hour) even for a prototype. Good signal of forward-looking design instinct.

**Gaps:**
- The original token bucket config had a math error (1 token/10s ≠ 10 req/5min) that wasn't self-caught. For a research document that's meant to be a specification, that's a meaningful miss. In a real interview you'd be expected to sanity-check your own numbers.
- Storage option 2 (Redis) and option 3 (dependencies) were left as stubs with no pros/cons initially — which contradicted the ground rule you yourself set.

---

### Prompting & Communication — 8.5 / 10

**Strengths:**
- Prompts were concise and directive without being vague. "Do as simple as possible. Instead of storage, use /data folder" is a well-scoped constraint that prevented over-engineering.
- Iterated with precise, single-concern feedback ("add .gitignore to phase 1", "add venv step to verification") rather than rewriting requirements wholesale. This is how strong engineers give feedback in code review too.
- Caught the missing `/data` folder post-implementation and called it out cleanly rather than silently accepting a broken state.

**Gaps:**
- The data folder omission was a planning gap surfaced at execution time — ideally that would have been caught during plan review, not after the files were created.
- One small prompt ambiguity: "read this plan into plan.md file" required a couple of back-and-forths. A big tech bar expects communication to be unambiguous on the first pass.

---

### Planning & Decomposition — 8 / 10

**Strengths:**
- Phase split (boilerplate → middleware) was correct. Getting a working skeleton before adding complexity is textbook incremental delivery.
- Iterated the plan in-place with targeted changes rather than starting over. Shows composure and efficiency.
- Verification steps were concrete and testable (not just "make sure it works" — actual HTTP calls with expected outputs).

**Gaps:**
- The plan didn't surface any edge cases: what if `request.client` is None (proxy/load balancer scenario)? What if the JSON file is corrupted mid-write? For a Big N bar, at least acknowledging known gaps in a plan is expected, even for a prototype.
- The `.gitignore` / `.venv` addition came reactively rather than proactively. A strong candidate would have included environment hygiene in the initial plan.

---

## 3 Strongest Points

**1. Ground rules before work begins**
Setting the `## Important` meta-section upfront — "justify every decision with pros/cons" — is a senior-level habit. Most candidates just start building. You defined the collaboration contract first, which prevented low-quality output downstream.

**2. Constraint-driven scoping**
"This is a prototype, do as simple as possible, use /data folder instead of storage" is a sharp, well-scoped constraint. You didn't over-specify, but you gave exactly enough context to prevent over-engineering. That's hard to teach.

**3. Targeted iteration**
Every feedback round was a single, precise concern — never "redo everything." `.gitignore`, venv step, data folder — each called out cleanly and independently. That's how strong engineers give code review feedback too.

---

## 3 Weaknesses to Improve

**1. Don't ship specs with unverified numbers**
The token bucket math error (1 token/10s ≠ 10 req/5min) slipped through because you didn't sanity-check your own calculation. Rule: any time you write a rate, a threshold, or a formula in a spec — verify it with a back-of-envelope check before moving on.

**2. Catch environment hygiene in planning, not in reaction**
`.gitignore`, `.venv`, the `/data` folder — all came up after the plan was drafted. These are table-stakes for any Python project. Build a personal checklist (venv, gitignore, secrets handling) you run through at the start of every plan.

**3. Acknowledge edge cases even if you don't solve them**
The plan never mentioned: what if `request.client` is None (proxy/load balancer scenario)? What if the JSON file is corrupted mid-write? At Big N, you don't have to solve every edge case in a prototype — but you're expected to name them. A one-line "known gaps" section in the plan would have moved you from Lean Hire to Hire.

---

## AI Coding Interview — How to Behave

### When Reviewing AI-Generated Code: Step by Step

The interviewer is not watching the AI — they are watching *you* review the AI. Your review process is the signal.

**Step 1 — Narrate your intent before reading**
Before you even scroll through the output, say out loud: "I'm going to check correctness first, then edge cases, then structure." This shows you have a review methodology, not just vibes.

**Step 2 — Verify it actually solves the problem**
Read the core logic and trace through the happy path mentally with a concrete example. Don't assume it's correct because it looks plausible. Say: "Let me trace through with input X — tokens = 10, elapsed = 45s, so new_tokens = min(10, 10 + 1.5) = 10. Correct."

**Step 3 — Check the edge cases explicitly**
Call out at least 2–3 edge cases by name:
- What if the input is empty / None?
- What happens on the first request (no prior state)?
- What if two requests arrive simultaneously?
- What if the file is missing or corrupted?

You don't have to fix all of them. Naming them is the signal.

**Step 4 — Check error handling and failure modes**
Look for: uncaught exceptions, missing null checks, unhandled I/O errors. Ask: "What happens if this line throws?"

**Step 5 — Check structure and naming**
Is the code readable? Are names clear? Is there unnecessary complexity? Would you approve this in a real PR?

**Step 6 — State what you'd change and why**
Don't just say "looks good." Say: "I'd add a null check on `request.client` here because behind a load balancer it can be None. Everything else I'd approve." One concrete, justified change is worth more than generic approval.

**Step 7 — Run it or test it if possible**
If the environment allows, actually execute the code and verify the output matches your expectation. Narrate what you expect *before* running it.

---

### When Waiting for AI to Answer: How to Interact with the Interviewer

Silence while the AI generates is the #1 mistake candidates make. The AI latency is dead air — use it.

**1. Narrate what you just prompted and why**
"I asked it to implement the middleware with an asyncio.Lock because we're on a single worker and need to prevent file corruption from concurrent requests." This proves the prompt was intentional, not trial-and-error.

**2. Predict the output before it appears**
"I expect it to generate a `BaseHTTPMiddleware` subclass with a `dispatch` method, load the JSON inside the lock, and call `call_next` outside of it." If you can predict the shape of the output, you demonstrate you understand the domain — not just the tool.

**3. Flag tradeoffs you're aware of**
"This file-based approach works for a single worker but would break under horizontal scaling — I'd swap the storage layer for Redis in production." You're showing architectural awareness without being asked.

**4. Ask the interviewer a clarifying question**
"Do you want me to handle the case where the data file is corrupted, or is that out of scope for the prototype?" This signals you think about edge cases and respect scope boundaries.

**5. Express controlled skepticism about the AI output**
"I'll verify the token refill formula before accepting it — that's the kind of off-by-one that looks right but isn't." Interviewers at Big N explicitly want to see that you don't blindly trust AI output.

**What to avoid:**
- Staring silently at the screen waiting for output
- Saying "let's see what it says" with no follow-up thought
- Accepting the output without any review
- Re-prompting immediately when output looks wrong without explaining why
