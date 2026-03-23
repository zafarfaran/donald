"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import ReportCard from "@/components/ReportCard";
import ShareButtons from "@/components/ShareButtons";
import ConversationBubble from "@/components/ConversationBubble";
import Navbar from "@/components/Navbar";
import { getReportCard } from "@/lib/api";
import { CrackingDiplomaIcon } from "@/components/icons";

export default function ReportPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [donaldStillTalking, setDonaldStillTalking] = useState(true);

  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 10;

    async function fetchReport() {
      try {
        const data = await getReportCard(sessionId);
        if (data) {
          setReport(data);
          setLoading(false);
          return;
        }
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(fetchReport, 2000);
        } else {
          setError(true);
          setLoading(false);
        }
      } catch {
        setError(true);
        setLoading(false);
      }
    }

    fetchReport();
  }, [sessionId]);

  if (loading) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center">
        <Navbar />
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-white/10 border-t-[var(--gold)] rounded-full animate-spin" />
          <p className="text-[var(--subtle)] text-sm font-display italic">compiling your vibe sheet...</p>
        </motion.div>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-6">
        <Navbar />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <CrackingDiplomaIcon size={56} className="mx-auto text-[var(--subtle)] mb-6" />
          <h1 className="font-display text-2xl mb-2">Vibe sheet not ready</h1>
          <p className="text-[var(--subtle)] text-sm mb-8 font-light">Donald hasn&apos;t finished yet. come back in a sec.</p>
          <a href="/" className="px-6 py-3 bg-[var(--gold)] text-black rounded-xl text-sm font-semibold hover:bg-[var(--gold-dim)] transition-colors glow-gold">
            Get your own check
          </a>
        </motion.div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(245,166,35,0.04) 0%, transparent 70%)" }} />
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-28 relative z-10">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="text-center mb-10">
          <p className="text-[var(--gold)] text-xs font-semibold tracking-[0.2em] uppercase mb-2">The Verdict</p>
          <h1 className="font-display text-3xl md:text-4xl">Your degree vibe sheet</h1>
          {donaldStillTalking && (
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
              className="text-[var(--subtle)] text-xs mt-2 font-light">
              Donald&apos;s still going in the bubble. this page is just the receipts.
            </motion.p>
          )}
        </motion.div>

        <ReportCard data={report} />

        <div className="mt-10">
          <ShareButtons sessionId={sessionId} grade={report.grade} />
        </div>

        <motion.a initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 3 }}
          href="/" className="mt-10 text-[var(--gold)] hover:text-[var(--gold-dim)] text-sm font-medium transition-colors font-display italic">
          get your own vibe check &rarr;
        </motion.a>
      </div>

      {/* Donald keeps talking via the floating bubble on the report page */}
      {donaldStillTalking && (
        <ConversationBubble
          sessionId={sessionId}
          onComplete={() => setDonaldStillTalking(false)}
        />
      )}
    </main>
  );
}
