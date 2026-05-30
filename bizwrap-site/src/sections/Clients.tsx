import { motion } from "framer-motion";
import { SectionHead } from "@/components/SectionHead";

const clients = ["Coca-Cola","PepsiCo","Cipla","ITC","Johnson & Johnson","MG Motor","HDFC Bank","Infosys","Maruti Suzuki","Dabur","Asian Paints","Wipro"];

export function Clients() {
  return (
    <section className="bg-ivory py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead center eyebrow="Trusted By" title="Enterprises across India gift with us" />
        <div className="grid grid-cols-3 gap-4 md:grid-cols-6">
          {clients.map((c, i) => (
            <motion.div
              key={c}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 0.78, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.04 }}
              whileHover={{ opacity: 1, y: -3 }}
              className="flex h-20 items-center justify-center rounded-2xl border border-border bg-card p-2 text-center font-display text-[15px] font-semibold text-emerald-deep transition hover:border-gold"
            >
              {c}
            </motion.div>
          ))}
        </div>
        <p className="mt-4 text-center text-xs italic text-muted-foreground">Logos shown as placeholders — replace with your genuine, authorised client logos before going live.</p>
      </div>
    </section>
  );
}
