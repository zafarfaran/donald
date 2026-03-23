"use client";

import { motion } from "framer-motion";
import { getDegreeTier } from "@/lib/degreeTier";

const testimonials = [
  { quote: "$180k degree, AI writes better essays. The numbers broke me.", name: "Sarah M.", info: "English Lit — NYU", grade: "D" as const },
  { quote: "67% automation risk + 90s of salary truth. Unwell.", name: "Marcus T.", info: "Comms — USC", grade: "F" as const },
  { quote: "CS degree, low replace risk. I'll take it.", name: "Priya K.", info: "CS — Georgia Tech", grade: "A" as const },
];

export default function TestimonialsSection() {
  return (
    <section className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.6 }} className="text-center mb-12">
          <span className="text-[var(--subtle)] text-xs font-semibold tracking-[0.2em] uppercase">Survivors</span>
          <h2 className="font-display text-3xl md:text-4xl mt-2">The <em>damage</em></h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => {
            const tier = getDegreeTier(t.grade);
            return (
            <motion.div key={t.name} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative p-7 rounded-2xl bg-[var(--card)] border border-white/5 overflow-visible">
              <div
                className={`absolute -top-2 right-3 rounded-xl px-2.5 py-1.5 flex items-center justify-center font-bold font-display border-2 bg-[var(--bg)] text-center leading-tight ${
                  tier.badge.length > 10 ? "max-w-[10.5rem] text-[9px]" : "min-w-[3.25rem] text-xs"
                }`}
                style={{ borderColor: tier.color, color: tier.color }}>{tier.badge}</div>
              <p className="font-display italic text-sm leading-relaxed mb-5">&ldquo;{t.quote}&rdquo;</p>
              <p className="text-sm font-semibold">{t.name}</p>
              <p className="text-[var(--subtle)] text-xs mt-0.5">{t.info}</p>
            </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
