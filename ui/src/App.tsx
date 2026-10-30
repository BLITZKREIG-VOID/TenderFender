import { BrowserRouter, Routes, Route } from "react-router-dom";
import TenderList from "./pages/TenderList";
import TenderDetail from "./pages/TenderDetail";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <span className="text-lg font-bold text-gray-900">
              🛡️ Tender Integrity
            </span>
            <span className="text-xs text-gray-400 ml-2">MVP</span>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<TenderList />} />
            <Route path="/tender/:id" element={<TenderDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
