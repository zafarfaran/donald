"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getPublicMetrics } from "@/lib/api";

const fallbackStats = [
  { value: "12,847+", label: "Degrees Cooked" },
  { value: "73%", label: "Got a C or Worse" },
  { value: "$2.4M", label: "Tuition in Shambles" },
  { value: "4.8/5", label: "Regret Score" },
];

export default function StatsSection() {
  const [stats, setStats] = useState(fallbackStats);

  useEffect(() => {
    let active = true;
    getPublicMetrics()
      .then((m) => {
        if (!active) return;
        setStats([
          { value: m.display.degrees_cooked, label: "Degrees Cooked" },
          { value: m.display.c_or_worse_pct, label: "Got a C or Worse" },
          { value: m.display.tuition_in_shambles, label: "Tuition in Shambles" },
          { value: m.display.regret_score, label: "Regret Score" },
        ]);
      })
      .catch(() => {
        // keep fallback values if API is unreachable
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="py-20 px-6 border-y border-white/5">
      <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.08 }}
            className="text-center">
            <div className="font-display text-3xl md:text-4xl text-gradient">{s.value}</div>
            <p className="text-[var(--subtle)] text-xs font-medium tracking-wide uppercase mt-1.5">{s.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
