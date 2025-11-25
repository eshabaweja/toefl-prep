import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import './App.css'
import QuizPage from './pages/QuizPage'

const AppLayout = () => (
  <div className="app-shell">
    <header className="app-header">
      <NavLink to="/" className="brand">
        TOEFL Prep
      </NavLink>

      <nav>
        <NavLink to="/quiz">Quiz</NavLink>
      </nav>

      <div className="header-actions">
        <span className="user-pill muted">Auth coming soon</span>
      </div>
    </header>

    <main>
      <Outlet />
    </main>
  </div>
)

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/quiz" replace />} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="*" element={<Navigate to="/quiz" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
