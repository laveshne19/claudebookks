import raw from "../catalog.json";

export type Product = {
  id: string; title: string; brand: string; cat: string;
  price: number; mrp: number; img: string; band: string;
};

export const PRODUCTS = raw as Product[];

export const BANDS: { key: string; label: string; short: string }[] = [
  { key: "all", label: "All budgets", short: "All" },
  { key: "b0", label: "Under ₹500", short: "< ₹500" },
  { key: "b1", label: "₹500 – ₹1,000", short: "₹500–1k" },
  { key: "b2", label: "₹1,000 – ₹1,500", short: "₹1k–1.5k" },
  { key: "b3", label: "₹1,500 – ₹2,000", short: "₹1.5k–2k" },
  { key: "b4", label: "₹2,000 – ₹3,000", short: "₹2k–3k" },
  { key: "b5", label: "₹3,000 – ₹5,000", short: "₹3k–5k" },
  { key: "b6", label: "₹5,000+", short: "₹5k+" },
];

export const CATEGORIES = Array.from(new Set(PRODUCTS.map((p) => p.cat))).sort();

export const BRANDS = Object.entries(
  PRODUCTS.reduce<Record<string, number>>((a, p) => ((a[p.brand] = (a[p.brand] || 0) + 1), a), {})
)
  .sort((a, b) => b[1] - a[1])
  .map(([b]) => b);

export const inr = (n: number) => "₹" + n.toLocaleString("en-IN");
export const discount = (p: Product) => (p.mrp > p.price ? Math.round((1 - p.price / p.mrp) * 100) : 0);

export const catIcon: Record<string, string> = {
  "Audio & Earbuds": "🎧",
  "Smartwatches & Wearables": "⌚",
  "Speakers": "🔊",
  "Home & Party Audio": "🎉",
  "Mobile Accessories": "🔌",
  "Smart Home & Security": "📷",
  "Lifestyle Gadgets": "🎁",
};
