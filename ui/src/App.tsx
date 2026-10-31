import { BrowserRouter, Routes, Route } from "react-router-dom";
import TenderList from "./pages/TenderList";
import TenderDetail from "./pages/TenderDetail";
import Navbar from "./components/Navbar";

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900">
        {/* Persistent Navigation Bar */}
        <Navbar />

        <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-4">
          <Routes>
            <Route path="/" element={<TenderList />} />
            <Route path="/tender/:id" element={<TenderDetail />} />
            <Route path="/tenders/:id" element={<TenderDetail />} />
          </Routes>
        </main>

        <footer className="mt-auto border-t border-gray-200 bg-white py-4">
          <div className="mx-auto max-w-7xl px-6 text-center text-xs text-slate-500">
            Tender Integrity Verification Platform • Enterprise Review Console
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;