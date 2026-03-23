"use client";

import { DonaldLogo } from "./icons";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-10 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <DonaldLogo className="text-[var(--subtle)]" />
          <span className="font-display text-sm text-[var(--subtle)]">Donald</span>
        </div>
        <p className="text-[var(--subtle)] text-xs text-center font-light">
          built with <a href="https://firecrawl.dev" target="_blank" rel="noopener noreferrer" className="text-[var(--fg)] hover:text-[var(--gold)] transition-colors">Firecrawl</a>
          {" & "}
          <a href="https://elevenlabs.io" target="_blank" rel="noopener noreferrer" className="text-[var(--fg)] hover:text-[var(--gold)] transition-colors">ElevenLabs</a>
          {" for "}<span className="text-[var(--fg)]">#ElevenHacks</span>
        </p>
        <p className="text-[var(--subtle)]/40 text-xs font-light">no degrees were harmed. feelings tho? absolutely.</p>
      </div>
    </footer>
  );
}
