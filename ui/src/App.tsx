import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import TenderList from "./pages/TenderList";
import TenderDetail from "./pages/TenderDetail";
import { ShieldCheck } from "lucide-react";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100 text-gray-950 flex flex-col font-sans">
        <header className="bg-black text-white border-b-4 border-gray-900 shadow-md">
          <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
            <Link
              to="/"
              className="flex items-center gap-3 group focus:outline-hidden focus:ring-4 focus:ring-blue-400 rounded-lg p-1"
            >
              <div className="p-1.5 bg-blue-600 rounded-md border-2 border-white group-hover:bg-blue-500 transition-colors">
                <ShieldCheck size={26} className="text-white" />
              </div>
              <div className="flex flex-col">
                <span className="text-xl sm:text-2xl font-black tracking-tight text-white uppercase group-hover:text-blue-300 transition-colors">
                  Tender Integrity Suite
                </span>
                <span className="text-xs font-bold text-gray-300 tracking-wider uppercase -mt-0.5">
                  Procurement Integrity & Collusion Detection MVP
                </span>
              </div>
            </Link>

            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider bg-gray-800 text-white border border-gray-600">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Presentation Mode
              </span>
              <span className="text-xs font-mono font-bold px-2 py-1 bg-blue-950 text-blue-200 border border-blue-800 rounded">
                v2.0
              </span>
            </div>
          </div>
        </header>

        <main className="max-w-7xl w-full mx-auto px-6 py-8 flex-1">
          <Routes>
            <Route path="/" element={<TenderList />} />
            <Route path="/tender/:id" element={<TenderDetail />} />
          </Routes>
        </main>

        <footer className="bg-white border-t-2 border-gray-300 py-4 mt-auto">
          <div className="max-w-7xl mx-auto px-6 text-center text-xs font-bold text-gray-700">
            Tender Integrity Verification Platform • High-Contrast Projector Display Mode Enabled
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
