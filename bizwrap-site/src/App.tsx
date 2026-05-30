import { Intro } from "@/components/brand/Intro";
import { TopBar } from "@/components/TopBar";
import { Navbar } from "@/sections/Navbar";
import { Hero } from "@/sections/Hero";
import { Marquee } from "@/sections/Marquee";
import { Story } from "@/sections/Story";
import { Shop } from "@/sections/Shop";
import { Collections } from "@/sections/Collections";
import { Metal } from "@/sections/Metal";
import { Vouchers } from "@/sections/Vouchers";
import { Modules } from "@/sections/Modules";
import { Clients } from "@/sections/Clients";
import { Testimonials } from "@/sections/Testimonials";
import { Blog } from "@/sections/Blog";
import { RFQ } from "@/sections/RFQ";
import { Footer } from "@/sections/Footer";
import { WhatsAppFab } from "@/sections/WhatsAppFab";

export default function App() {
  return (
    <div className="min-h-screen bg-ivory">
      <Intro />
      <TopBar />
      <Navbar />
      <Hero />
      <Marquee />
      <Story />
      <Shop />
      <Collections />
      <Metal />
      <Vouchers />
      <Modules />
      <Clients />
      <Testimonials />
      <Blog />
      <RFQ />
      <Footer />
      <WhatsAppFab />
    </div>
  );
}
