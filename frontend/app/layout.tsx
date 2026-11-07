import "./globals.css";
export const metadata = { title: "OmniPrep" };
export default function L({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
