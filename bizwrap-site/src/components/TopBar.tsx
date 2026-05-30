import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, X, Share, Plus } from "lucide-react";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";

/** Slim ribbon pinned to the very top — the single "install app" entry point. */
export function TopBar() {
  const { canInstall, isIOS, promptInstall } = useInstallPrompt();
  const [dismissed, setDismissed] = useState(false);
  const [showIOS, setShowIOS] = useState(false);

  useEffect(() => {
    const show = canInstall && !dismissed;
    document.documentElement.classList.toggle("has-topbar", show);
    return () => document.documentElement.classList.remove("has-topbar");
  }, [canInstall, dismissed]);

  if (!canInstall || dismissed) return null;

  const handle = async () => {
    if (isIOS) { setShowIOS(true); return; }
    await promptInstall();
  };

  return (
    <>
      <motion.div
        initial={{ y: -40 }}
        animate={{ y: 0 }}
        transition={{ delay: 3, duration: 0.5 }}
        className="fixed inset-x-0 top-0 z-[70] flex items-center justify-center gap-3 px-4 py-2 text-sm text-white"
        style={{ background: "linear-gradient(90deg,#0A3F2E,#0E5C43,#0A3F2E)" }}
      >
        <span className="hidden sm:inline">📲 Get the BizWrap app — faster browsing, works offline.</span>
        <button onClick={handle} className="inline-flex items-center gap-1.5 rounded-full bg-gold px-3.5 py-1 text-[13px] font-semibold text-emerald-deep transition hover:bg-gold-soft">
          <Download className="h-3.5 w-3.5" /> Install App
        </button>
        <button onClick={() => setDismissed(true)} aria-label="Dismiss" className="absolute right-3 text-white/60 hover:text-white">
          <X className="h-4 w-4" />
        </button>
      </motion.div>

      <AnimatePresence>
        {showIOS && (
          <motion.div className="fixed inset-0 z-[200] flex items-end justify-center bg-black/50 p-4 sm:items-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowIOS(false)}>
            <motion.div className="w-full max-w-sm rounded-3xl bg-card p-6"
              initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }} onClick={(e) => e.stopPropagation()}>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-display text-xl text-emerald-deep">Install BizWrap</h3>
                <button onClick={() => setShowIOS(false)}><X className="h-5 w-5 text-muted-foreground" /></button>
              </div>
              <p className="text-sm text-muted-foreground">Add BizWrap to your home screen:</p>
              <ol className="mt-4 space-y-3 text-sm">
                <li className="flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">1</span> Tap <Share className="mx-1 inline h-4 w-4 text-cta" /> Share in Safari</li>
                <li className="flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">2</span> Choose <b className="mx-1">Add to Home Screen</b> <Plus className="inline h-4 w-4" /></li>
                <li className="flex items-center gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">3</span> Tap <b className="ml-1">Add</b> — done!</li>
              </ol>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
