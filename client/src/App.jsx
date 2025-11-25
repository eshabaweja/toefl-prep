import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import './App.css'
import { AuthProvider, useAuth } from './context/AuthContext'
import AuthPage from './pages/AuthPage'
import DashboardPage from './pages/DashboardPage'
import QuizPage from './pages/QuizPage'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isAuthenticating } = useAuth()

  if (isAuthenticating) {
    return <p className="muted center">Checking your session…</p>
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  return children
}

const AppLayout = () => {
  const { isAuthenticated, user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink to="/" className="brand">
          TOEFL Prep
        </NavLink>

        <nav>
          {isAuthenticated ? (
            <>
              <NavLink to="/">Dashboard</NavLink>
              <NavLink to="/quiz">Quiz</NavLink>
            </>
          ) : (
            <NavLink to="/auth">Sign in</NavLink>
          )}
        </nav>

        <div className="header-actions">
          {isAuthenticated ? (
            <>
              <span className="user-pill">
                {user?.fullName || user?.name || user?.email || 'You'}
              </span>
              <button type="button" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <NavLink to="/auth" className="button ghost">
              Get started
            </NavLink>
          )}
        </div>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/auth" element={<AuthPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/quiz"
              element={
                <ProtectedRoute>
                  <QuizPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
