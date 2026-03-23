"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ConversationBubble from "@/components/ConversationBubble";
import DonaldConversation from "@/components/DonaldConversation";
import VoiceActivityPanel, { type VoiceActivityRow } from "@/components/VoiceActivityPanel";
import Navbar from "@/components/Navbar";
import { createSession, createVoiceSession, fetchVoiceActivity, scrapeLinkedIn } from "@/lib/api";
import { BurningCapIcon, MicIcon } from "@/components/icons";

const PHONE_NUMBER = process.env.NEXT_PUBLIC_DONALD_PHONE || "+1 (800) 555-0199";
const ELEVENLABS_AGENT_CONFIGURED = !!process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;

function PhoneIcon({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={className}>
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function GlobeIcon({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function LinkIcon({ size = 16, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className={className}>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

export default function RoastPage() {
  const router = useRouter();
  const [step, setStep] = useState<"choose" | "linkedin" | "webcall" | "phonecall">("choose");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [callMethod, setCallMethod] = useState<"web" | "phone" | null>(null);
  const [liveActivity, setLiveActivity] = useState<VoiceActivityRow[]>([]);
  const [serverActivity, setServerActivity] = useState<VoiceActivityRow[]>([]);
  const [activityPoll, setActivityPoll] = useState<{ ok: boolean; error?: string; at: number }>({
    ok: true,
    at: 0,
  });

  useEffect(() => {
    setLiveActivity([]);
    setServerActivity([]);
    setActivityPoll({ ok: true, at: 0 });
  }, [sessionId]);

  const appendLiveActivity = useCallback((row: VoiceActivityRow) => {
    setLiveActivity((prev) => [...prev, row]);
  }, []);

  useEffect(() => {
    if (!sessionId || step !== "webcall" || !ELEVENLABS_AGENT_CONFIGURED) return;
    let cancelled = false;
    const poll = async () => {
      const result = await fetchVoiceActivity(sessionId);
      if (cancelled) return;
      setActivityPoll({
        ok: result.ok,
        error: result.error,
        at: Date.now(),
      });
      if (result.ok) {
        setServerActivity(
          result.items.map((i) => ({
            id: `srv-${i.id}`,
            ts: new Date(i.ts).getTime(),
            source: "server" as const,
            event: i.event,
            title: i.title,
            detail: i.detail || undefined,
            data: i.data,
          }))
        );
      } else {
        setServerActivity([]);
      }
    };
    poll();
    const id = setInterval(poll, 1200);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [sessionId, step]);

  const mergedActivity = useMemo(
    () => [...liveActivity, ...serverActivity].sort((a, b) => a.ts - b.ts),
    [liveActivity, serverActivity]
  );

  const createAndStart = async (method: "web" | "phone", linkedin?: string) => {
    setLoading(true);
    setCallMethod(method);
    try {
      if (linkedin) {
        const result = await scrapeLinkedIn(linkedin);
        const session = await createSession(
          result.success
            ? { name: result.name || "", degree: result.degree || "", university: result.university || "", graduation_year: result.graduation_year || 2020, current_job: result.current_job || "", source: "linkedin" }
            : { name: "", degree: "", university: "", graduation_year: 0, current_job: "", source: "manual" }
        );
        setSessionId(session.session_id);
      } else {
        const session = await createVoiceSession();
        setSessionId(session.session_id);
      }
    } catch {
      const session = await createVoiceSession();
      setSessionId(session.session_id);
    }
    setLoading(false);
    setStep(method === "web" ? "webcall" : "phonecall");
  };

  return (
    <main className="relative min-h-screen flex flex-col overflow-x-hidden">
      <Navbar />
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse at center 30%, rgba(245,166,35,0.03) 0%, transparent 50%)" }} />

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-24 relative z-10">
        <AnimatePresence mode="wait">

          {/* ===== STEP 1: Choose how to talk to Donald ===== */}
          {step === "choose" && (
            <motion.div key="choose" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4 }} className="w-full max-w-lg mx-auto text-center">

              <BurningCapIcon size={40} className="text-[var(--gold)] mx-auto mb-6" />
              <h1 className="font-display text-3xl md:text-4xl mb-2">How do you want to <em>talk to Donald?</em></h1>
              <p className="text-[var(--subtle)] text-sm font-light mb-10 max-w-md mx-auto leading-relaxed">
                web or phone. same data, same voice reality check. pick your lane.
              </p>

              {/* Two cards */}
              <div className="grid sm:grid-cols-2 gap-4 mb-8">
                {/* Web call card */}
                <motion.button
                  onClick={() => createAndStart("web")}
                  disabled={loading}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                  className="group p-6 rounded-2xl bg-[var(--card)] border border-white/8 hover:border-[var(--gold)]/30 text-left transition-all disabled:opacity-50"
                >
                  <div className="w-12 h-12 rounded-xl bg-[var(--gold)]/10 border border-[var(--gold)]/20 flex items-center justify-center mb-4 group-hover:bg-[var(--gold)]/15 transition-colors">
                    <GlobeIcon size={22} className="text-[var(--gold)]" />
                  </div>
                  <h3 className="text-base font-semibold mb-1">Web Call</h3>
                  <p className="text-[var(--subtle)] text-xs font-light leading-relaxed">
                    talk to Donald right here in your browser. no download, no signup. just vibes and regret.
                  </p>
                  <div className="mt-4 flex items-center gap-1.5 text-[var(--gold)] text-xs font-semibold">
                    <MicIcon size={14} />
                    start now
                  </div>
                </motion.button>

                {/* Phone call card */}
                <motion.button
                  onClick={() => setStep("phonecall")}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                  className="group p-6 rounded-2xl bg-[var(--card)] border border-white/8 hover:border-[var(--gold)]/30 text-left transition-all"
                >
                  <div className="w-12 h-12 rounded-xl bg-[var(--red)]/10 border border-[var(--red)]/20 flex items-center justify-center mb-4 group-hover:bg-[var(--red)]/15 transition-colors">
                    <PhoneIcon size={22} className="text-[var(--red)]" />
                  </div>
                  <h3 className="text-base font-semibold mb-1">Phone Call</h3>
                  <p className="text-[var(--subtle)] text-xs font-light leading-relaxed">
                    call Donald on an actual phone number. perfect for tiktok content. &quot;I called this number and it destroyed me.&quot;
                  </p>
                  <div className="mt-4 flex items-center gap-1.5 text-[var(--red)] text-xs font-semibold">
                    <PhoneIcon size={14} />
                    get the number
                  </div>
                </motion.button>
              </div>

              {/* Optional LinkedIn shortcut */}
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-white/5" />
                <span className="text-[var(--subtle)]/50 text-xs">optional: speed things up</span>
                <div className="flex-1 h-px bg-white/5" />
              </div>

              <div className="flex gap-2 max-w-sm mx-auto">
                <div className="relative flex-1">
                  <LinkIcon size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--subtle)]/40" />
                  <input
                    type="url"
                    placeholder="Paste LinkedIn URL"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    className="w-full pl-9 pr-4 py-2.5 bg-[var(--card)] border border-white/8 rounded-xl text-xs text-[var(--fg)] placeholder:text-[var(--subtle)]/40 focus:outline-none focus:border-[var(--gold)]/30 transition-all"
                  />
                </div>
                {linkedinUrl && (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    onClick={() => createAndStart("web", linkedinUrl)}
                    disabled={loading}
                    className="px-4 py-2.5 bg-[var(--gold)] text-black text-xs font-bold rounded-xl hover:bg-[var(--gold-dim)] transition-colors disabled:opacity-50"
                  >
                    Go
                  </motion.button>
                )}
              </div>

              <p className="text-[var(--subtle)]/30 text-[10px] mt-6">
                we don&apos;t store anything. Donald forgets you the second the call ends.
              </p>
            </motion.div>
          )}

          {/* ===== STEP 2a: Phone call view ===== */}
          {step === "phonecall" && (
            <motion.div key="phone" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4 }} className="w-full max-w-sm mx-auto text-center">

              <div className="w-20 h-20 rounded-full bg-[var(--red)]/10 border-2 border-[var(--red)]/30 flex items-center justify-center mx-auto mb-6">
                <PhoneIcon size={32} className="text-[var(--red)]" />
              </div>

              <h1 className="font-display text-3xl mb-2">Call <em>Donald</em></h1>
              <p className="text-[var(--subtle)] text-sm font-light mb-8">
                dial the number below. Donald will pick up and start asking about your degree. no escape.
              </p>

              {/* Phone number display */}
              <a
                href={`tel:${PHONE_NUMBER.replace(/\D/g, "")}`}
                className="block mb-6 px-6 py-5 bg-[var(--card)] border border-white/10 hover:border-[var(--red)]/30 rounded-2xl transition-all group"
              >
                <p className="text-2xl font-bold tracking-wider group-hover:text-[var(--red)] transition-colors">
                  {PHONE_NUMBER}
                </p>
                <p className="text-[var(--subtle)] text-xs mt-1.5">tap to call on mobile</p>
              </a>

              {/* Tips */}
              <div className="space-y-2.5 text-left bg-[var(--card)] rounded-xl p-5 border border-white/5 mb-6">
                <p className="text-xs text-[var(--subtle)] font-semibold uppercase tracking-wider mb-3">pro tips for max content</p>
                <div className="flex items-start gap-2.5">
                  <span className="text-sm">📱</span>
                  <p className="text-xs text-[var(--subtle)] font-light">put on speaker and screen record for tiktok</p>
                </div>
                <div className="flex items-start gap-2.5">
                  <span className="text-sm">🎭</span>
                  <p className="text-xs text-[var(--subtle)] font-light">film your reaction. the face when Donald drops the S&P 500 math is content gold</p>
                </div>
                <div className="flex items-start gap-2.5">
                  <span className="text-sm">🏷️</span>
                  <p className="text-xs text-[var(--subtle)] font-light">tag @firecrawl @elevenlabs #ElevenHacks for max clout</p>
                </div>
              </div>

              <button
                onClick={() => setStep("choose")}
                className="text-[var(--subtle)] text-xs hover:text-[var(--fg)] transition-colors"
              >
                ← back to options
              </button>
            </motion.div>
          )}

          {/* ===== STEP 2b: Web call active ===== */}
          {step === "webcall" && (
            <motion.div
              key="webcall"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
              className={`w-full mx-auto ${ELEVENLABS_AGENT_CONFIGURED ? "max-w-5xl" : "max-w-lg"} text-center`}
            >
              <h1 className="font-display text-3xl md:text-4xl mb-2">The Call Is <em>Live</em></h1>
              {ELEVENLABS_AGENT_CONFIGURED ? (
                <p className="text-[var(--subtle)] text-sm font-light mb-6 max-w-xl mx-auto">
                  The panel on the right shows what you said and the facts Donald’s pulling — you’ll see a progress bar while he’s digging.
                </p>
              ) : (
                <p className="text-[var(--subtle)] text-sm font-light mb-4">
                  Donald is in the bubble. bottom right corner. go talk to him bestie.
                </p>
              )}
              {ELEVENLABS_AGENT_CONFIGURED && sessionId ? (
                <div className="grid lg:grid-cols-2 gap-6 items-start text-left w-full">
                  <div className="flex flex-col items-center lg:items-center mx-auto w-full max-w-md">
                    <DonaldConversation
                      sessionId={sessionId}
                      onComplete={() => router.push(`/report/${sessionId}`)}
                      onSdkActivity={appendLiveActivity}
                    />
                  </div>
                  <VoiceActivityPanel
                    items={mergedActivity}
                    pollOk={activityPoll.ok}
                    pollError={activityPoll.error}
                    pollAt={activityPoll.at}
                  />
                </div>
              ) : null}
              {!ELEVENLABS_AGENT_CONFIGURED && (
                <div className="flex items-center justify-center gap-2 text-[var(--gold)] text-xs">
                  <span className="w-2 h-2 rounded-full bg-[var(--gold)] animate-pulse" />
                  voice call active (demo)
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Demo-only bubble when no ElevenLabs agent id */}
      {step === "webcall" && sessionId && !ELEVENLABS_AGENT_CONFIGURED && (
        <ConversationBubble sessionId={sessionId} onComplete={() => router.push(`/report/${sessionId}`)} />
      )}
    </main>
  );
}
