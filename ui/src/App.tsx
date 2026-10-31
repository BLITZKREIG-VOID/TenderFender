import { BrowserRouter, Routes, Route } from "react-router-dom";
import TenderList from "./pages/TenderList";
import TenderDetail from "./pages/TenderDetail";
import About from "./pages/About";
import Navbar from "./components/Navbar";
import { Beams } from "./components/ui/beams";

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col font-sans text-slate-900">
        {/* Beams WebGL background — covers viewport, behind content */}
        <Beams className="fixed inset-0 z-[-1] opacity-50" />

        {/* Persistent Navigation Bar */}
        <Navbar />

        <main className="relative z-10 min-h-screen mx-auto w-full max-w-7xl px-6 py-4 flex-1">
          <Routes>
            <Route path="/" element={<TenderList />} />
            <Route path="/tender/:id" element={<TenderDetail />} />
            <Route path="/tenders/:id" element={<TenderDetail />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>

        <footer className="mt-auto border-t border-gray-200 py-4">
          <div className="mx-auto max-w-7xl px-6 text-center text-xs text-slate-500">
            Tender Integrity Verification Platform • Enterprise Review Console
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
