import { Logo } from "@/components/brand/Logo";

export function Footer() {
  return (
    <footer className="bg-emerald-deep pt-16 pb-8 text-white/72">
      <div className="mx-auto max-w-[1280px] px-6">
        <div className="grid grid-cols-1 gap-9 border-b border-white/10 pb-10 md:grid-cols-[1.4fr_1fr_1fr_1.2fr]">
          <div>
            <Logo light />
            <p className="mt-4 max-w-xs text-sm font-light leading-relaxed">Curating memorable corporate gifting experiences for enterprises across India since 2019. Premium gifts, stronger relationships.</p>
          </div>
          <FootCol title="Collections" links={["Audio & Earbuds", "Smartwatches", "Speakers", "Gift Vouchers", "Festive Hampers"]} />
          <FootCol title="Solutions" links={["Bulk Orders", "Corporate Branding", "Vendor Portal", "Onboarding Kits", "Campaign Manager"]} />
          <div className="text-sm font-light leading-loose">
            <h5 className="mb-4 text-[12.5px] font-semibold uppercase tracking-[0.14em] text-white">Contact</h5>
            <b className="text-gold-soft">+91 9115513336</b><br />
            aanchal.b@bizwrapindia.com<br />
            www.bizwrapindia.com<br /><br />
            007, 2nd Floor, Emaar The Palm Square, Sector 66, Golf Course Road Extension, Gurugram, Haryana
          </div>
        </div>
        <div className="flex flex-wrap justify-between gap-3 pt-6 text-[12.5px] text-white/45">
          <span>© 2026 BizWrap India. All rights reserved.</span>
          <span>Privacy Policy · Terms & Conditions · GSTIN: 06XXXXXXXXXXXZX</span>
        </div>
      </div>
    </footer>
  );
}

function FootCol({ title, links }: { title: string; links: string[] }) {
  return (
    <div>
      <h5 className="mb-4 text-[12.5px] font-semibold uppercase tracking-[0.14em] text-white">{title}</h5>
      {links.map((l) => <a key={l} href="#" className="mb-2.5 block text-sm font-light transition hover:text-gold-soft">{l}</a>)}
    </div>
  );
}
