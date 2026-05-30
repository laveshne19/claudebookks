import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Phone, Mail, MapPin } from "lucide-react";

const benefits = ["Tiered volume pricing & GST invoicing", "Branding: laser, UV, logo printing, embroidery", "Pan-India delivery & dispatch tracking", "Dedicated account manager for 500+ qty"];

export function RFQ() {
  const [sent, setSent] = useState(false);
  return (
    <section id="rfq" className="py-20 text-white" style={{ background: "linear-gradient(150deg,#0E5C43,#0A3F2E)" }}>
      <div className="mx-auto grid max-w-[1280px] grid-cols-1 items-start gap-12 px-6 md:grid-cols-[0.9fr_1.1fr]">
        <motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">Request for Quotation</span>
          <h2 className="mt-3 font-display text-[clamp(28px,3.4vw,40px)] font-medium text-balance">Let's curate your next corporate gift</h2>
          <p className="mt-4 font-light text-white/75">Tell us your occasion, quantity and budget. Our team responds within one business day.</p>
          <ul className="mt-6 space-y-3">
            {benefits.map((b) => (
              <li key={b} className="flex items-center gap-3 text-[14.5px] text-white/90">
                <span className="flex h-[21px] w-[21px] shrink-0 items-center justify-center rounded-full bg-gold text-emerald-deep"><Check className="h-3 w-3" strokeWidth={3} /></span>
                {b}
              </li>
            ))}
          </ul>
          <div className="mt-7 space-y-2 text-sm text-white/85">
            <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-gold-soft" /> <b className="text-gold-soft">+91 9115513336</b></p>
            <p className="flex items-center gap-2"><Mail className="h-4 w-4 text-gold-soft" /> aanchal.b@bizwrapindia.com</p>
            <p className="flex items-center gap-2"><MapPin className="h-4 w-4 text-gold-soft" /> Emaar The Palm Square, Sector 66, Golf Course Rd Ext., Gurugram</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="rounded-[22px] border border-white/14 bg-white/[0.05] p-7 backdrop-blur-md">
          {sent ? (
            <div className="flex h-full min-h-[340px] flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gold text-emerald-deep"><Check className="h-8 w-8" strokeWidth={3} /></div>
              <h3 className="font-display text-2xl">Request received!</h3>
              <p className="mt-2 text-white/70">In the live build this is stored as a lead and emailed to aanchal.b@bizwrapindia.com. Our team will respond within one business day.</p>
            </div>
          ) : (
            <div className="space-y-3.5">
              <div className="grid grid-cols-2 gap-3.5">
                <Field label="Company Name" ph="Acme Pvt Ltd" />
                <Field label="Contact Person" ph="Your name" />
              </div>
              <div className="grid grid-cols-2 gap-3.5">
                <Field label="Email" ph="you@company.com" />
                <Field label="Phone" ph="+91" />
              </div>
              <div className="grid grid-cols-2 gap-3.5">
                <Field label="Quantity" ph="e.g. 250" />
                <Field label="Budget / unit (₹)" ph="e.g. 1500" />
              </div>
              <div className="grid grid-cols-2 gap-3.5">
                <Sel label="Occasion" opts={["Festive / Diwali", "Employee Onboarding", "Client / Executive", "Annual Day / Rewards"]} />
                <Sel label="Branding" opts={["Logo Printing", "Laser Engraving", "UV Printing", "Embroidery", "None"]} />
              </div>
              <button onClick={() => setSent(true)} className="mt-1 w-full rounded-full bg-gold py-3.5 font-semibold text-emerald-deep transition hover:bg-gold-soft">Submit RFQ →</button>
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}

function Field({ label, ph }: { label: string; ph: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[12px] text-white/72">{label}</span>
      <input placeholder={ph} className="w-full rounded-xl border border-white/18 bg-white/[0.07] px-3.5 py-3 text-sm text-white outline-none placeholder:text-white/40 focus:border-gold" />
    </label>
  );
}
function Sel({ label, opts }: { label: string; opts: string[] }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[12px] text-white/72">{label}</span>
      <select className="w-full rounded-xl border border-white/18 bg-white/[0.07] px-3.5 py-3 text-sm text-white outline-none focus:border-gold [&>option]:text-ink">
        {opts.map((o) => <option key={o}>{o}</option>)}
      </select>
    </label>
  );
}
