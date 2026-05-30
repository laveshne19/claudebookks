import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

export function Intro() {
  const [done, setDone] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDone(true), 2700);
    return () => clearTimeout(t);
  }, []);

  return (
    <AnimatePresence>
      {!done && (
        <motion.div
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center"
          style={{ background: "radial-gradient(120% 100% at 50% 40%, #0f6b4e 0%, #0E5C43 40%, #0A3F2E 100%)" }}
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6 }}
          onClick={() => setDone(true)}
        >
          <div className="relative h-[170px] w-[190px]">
            {/* burst */}
            <motion.div
              className="absolute left-1/2 top-[42px] -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{ background: "radial-gradient(circle, #fff, #E4C97A 40%, transparent 70%)" }}
              initial={{ width: 8, height: 8, opacity: 0 }}
              animate={{ width: [8, 8, 380, 520], height: [8, 8, 380, 520], opacity: [0, 1, 0.7, 0] }}
              transition={{ duration: 1.6, delay: 1.1, times: [0, 0.1, 0.6, 1] }}
            />
            {/* sparks */}
            {Array.from({ length: 8 }).map((_, i) => {
              const a = (i / 8) * Math.PI * 2;
              return (
                <motion.span
                  key={i}
                  className="absolute left-1/2 top-[44px] h-2 w-2 rounded-full bg-gold-soft"
                  initial={{ x: 0, y: 0, opacity: 0, scale: 0.4 }}
                  animate={{ x: Math.cos(a) * 150, y: Math.sin(a) * 150, opacity: [0, 1, 0], scale: 1 }}
                  transition={{ duration: 1.3, delay: 1.2 }}
                />
              );
            })}
            {/* lid + bow */}
            <motion.div
              className="absolute left-1/2 top-[14px] z-20 h-[30px] w-[46px] -translate-x-1/2"
              initial={{ y: 0, rotate: 0 }}
              animate={{ y: [0, 0, -110, -260], rotate: [0, 0, -16, -42], opacity: [1, 1, 1, 0] }}
              transition={{ duration: 2.4, times: [0, 0.3, 0.55, 1], ease: "easeOut" }}
            >
              <span className="absolute left-0 h-[30px] w-[22px] -rotate-[20deg] rounded-[50%/60%_60%_40%_40%]" style={{ background: "linear-gradient(#C9A227,#a9842a)" }} />
              <span className="absolute right-0 h-[30px] w-[22px] rotate-[20deg] rounded-[50%/60%_60%_40%_40%]" style={{ background: "linear-gradient(#C9A227,#a9842a)" }} />
            </motion.div>
            <motion.div
              className="absolute left-1/2 top-[30px] z-10 h-[42px] w-[168px] -translate-x-1/2 rounded-lg shadow-xl"
              style={{ background: "linear-gradient(160deg,#fff,#E4C97A)" }}
              initial={{ y: 0, rotate: 0 }}
              animate={{ y: [0, 4, -90, -220], rotate: [0, 0, -14, -30], opacity: [1, 1, 1, 0] }}
              transition={{ duration: 2.4, times: [0, 0.32, 0.55, 1], ease: "easeOut" }}
            >
              <span className="absolute left-1/2 top-0 h-full w-6 -translate-x-1/2 bg-gold" />
            </motion.div>
            {/* base */}
            <motion.div
              className="absolute bottom-0 left-1/2 h-[96px] w-[150px] -translate-x-1/2 rounded-lg"
              style={{ background: "linear-gradient(160deg,#E4C97A,#C9A227)", boxShadow: "inset 0 -10px 20px rgba(0,0,0,.15)" }}
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <span className="absolute left-1/2 top-0 h-full w-6 -translate-x-1/2 bg-white/35" />
            </motion.div>
          </div>
          <motion.div
            className="mt-8 font-display text-3xl text-white"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.5, duration: 0.7 }}
          >
            BizWrap<span className="text-gold-soft"> India</span>
          </motion.div>
          <motion.div
            className="mt-2 text-[13px] uppercase tracking-[0.18em] text-white/70"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.8, duration: 0.7 }}
          >
            Unwrapping memorable corporate gifting
          </motion.div>
          <div className="absolute bottom-8 text-xs tracking-wider text-white/50">tap to skip</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
