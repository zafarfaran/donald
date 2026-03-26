# Donald

Donald is a voice-first AI that roasts your degree, school, and career choices using real-world signals — salary ranges, tuition, job-market stress, and AI exposure — then drops a blunt grade and practical “how to not get cooked” moves. It is comedy-first; the numbers are the setup.

**Try it:** [heyitsdonald.com](https://heyitsdonald.com)

## What Donald does

- **Live voice conversation** — You talk; Donald reacts in character (high-energy, roast-comedy tone) and walks you through setup, research-backed roasting, and optional follow-ups.
- **Report card** — After a session you get a structured breakdown (grade, stats, tips) aligned with what the pipeline actually computed, not vibes-only numbers.
- **Roast + reality check** — The main flow combines jokes with data-backed angles (tuition vs alternatives, role vs market averages, AI-replacement framing where relevant) so the roast and the “verdict” stay connected.

## Underlying capabilities

- **Conversational AI (voice)** — Real-time speech in and out via ElevenLabs Conversational AI; WebRTC sessions can use server-minted tokens when the agent is not fully public.
- **Client-side tools** — For the full product, tools like `research_degree` run in the user’s browser and call your backend so research can work in local dev without exposing localhost to ElevenLabs’ servers directly.
- **Research pipeline** — Backend jobs combine web retrieval (e.g. targeted search/scrape) with LLM analysis to produce structured report fields, tips, and citations-style source lists used in the roast and UI.
- **Session + persistence** — Sessions and report snapshots are tied together so a shareable report view can reflect what happened in voice or form flows.
- **Marketing / demo variants** — Separate prompt flavors exist (e.g. comedy-only roasts for clips) that intentionally skip full research tooling; behavior depends on which agent configuration is live in the ElevenLabs project.

Donald is not a generic chatbot: the product is built around **roast + data + voice**, with guardrails around protected traits and distress.
