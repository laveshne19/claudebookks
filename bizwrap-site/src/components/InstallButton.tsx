import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, Share, Plus, X } from "lucide-react";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";

export function InstallButton({ scrolled }: { scrolled: boolean }) {
  const { canInstall, isIOS, promptInstall } = useInstallPrompt();
  const [showIOS, setShowIOS] = useState(false);

  if (!canInstall) return null;

  const handle = async () => {
    if (isIOS) { setShowIOS(true); return; }
    await promptInstall();
  };

  return (
    <>
      <button
        onClick={handle}
        className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2.5 text-sm font-semibold transition ${
          scrolled ? "bg-emerald text-white hover:bg-emerald-light" : "bg-white/15 text-white backdrop-blur hover:bg-white/25"
        }`}
      >
        <Download className="h-4 w-4" /> Install App
      </button>

      <AnimatePresence>
        {showIOS && (
          <motion.div
            className="fixed inset-0 z-[200] flex items-end justify-center bg-black/50 p-4 sm:items-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowIOS(false)}
          >
            <motion.div
              className="w-full max-w-sm rounded-3xl bg-card p-6"
              initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-display text-xl text-emerald-deep">Install BizWrap</h3>
                <button onClick={() => setShowIOS(false)}><X className="h-5 w-5 text-muted-foreground" /></button>
              </div>
              <p className="text-sm text-muted-foreground">Add BizWrap to your home screen for an app-like experience:</p>
              <ol className="mt-4 space-y-3 text-sm">
                <li className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">1</span>
                  Tap the <Share className="mx-1 inline h-4 w-4 text-cta" /> Share button in Safari
                </li>
                <li className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">2</span>
                  Choose <b className="mx-1">Add to Home Screen</b> <Plus className="inline h-4 w-4" />
                </li>
                <li className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald text-white">3</span>
                  Tap <b className="ml-1">Add</b> — done!
                </li>
              </ol>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
