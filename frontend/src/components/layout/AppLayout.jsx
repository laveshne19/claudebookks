import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppLayout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title={title} subtitle={subtitle} />
        <main className="flex-1 p-4 md:p-6 lg:p-8 animate-fade-in" data-testid="page-content">
          <div className="max-w-screen-2xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
