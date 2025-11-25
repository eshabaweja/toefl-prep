import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const initialFormState = {
  fullName: '',
  email: '',
  password: '',
  targetScore: '100',
}

const AuthPage = () => {
  const navigate = useNavigate()
  const { signup, login, isAuthenticated, isAuthenticating } = useAuth()
  const [mode, setMode] = useState('login')
  const [formValues, setFormValues] = useState(initialFormState)
  const [feedback, setFeedback] = useState({ error: null, success: null })

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleInputChange = (event) => {
    const { name, value } = event.target
    setFormValues((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setFeedback({ error: null, success: null })

    try {
      if (mode === 'signup') {
        await signup(formValues)
        setFeedback({
          success: 'Account created. Redirecting you to your dashboard...',
          error: null,
        })
      } else {
        await login({
          email: formValues.email,
          password: formValues.password,
        })
      }

      navigate('/', { replace: true })
    } catch (error) {
      setFeedback({ error: error.message, success: null })
    }
  }

  const toggleMode = (nextMode) => {
    setMode(nextMode)
    setFeedback({ error: null, success: null })
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <header>
          <p className="eyebrow">TOEFL PREP</p>
          <h1>{mode === 'signup' ? 'Create your account' : 'Welcome back'}</h1>
          <p>Sign up or sign in to sync your quiz sessions and lesson plan.</p>
        </header>

        <div className="auth-toggle">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => toggleMode('login')}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'active' : ''}
            onClick={() => toggleMode('signup')}
          >
            Sign up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'signup' && (
            <label>
              <span>Full name</span>
              <input
                name="fullName"
                type="text"
                placeholder="Jane Doe"
                value={formValues.fullName}
                onChange={handleInputChange}
                required
              />
            </label>
          )}

          <label>
            <span>Email</span>
            <input
              name="email"
              type="email"
              placeholder="name@example.com"
              value={formValues.email}
              onChange={handleInputChange}
              required
            />
          </label>

          <label>
            <span>Password</span>
            <input
              name="password"
              type="password"
              placeholder="At least 8 characters"
              value={formValues.password}
              onChange={handleInputChange}
              required
              minLength={8}
            />
          </label>

          {mode === 'signup' && (
            <label>
              <span>Target score</span>
              <input
                name="targetScore"
                type="number"
                min={80}
                max={120}
                value={formValues.targetScore}
                onChange={handleInputChange}
              />
            </label>
          )}

          {feedback.error && <p className="form-feedback error">{feedback.error}</p>}
          {feedback.success && <p className="form-feedback success">{feedback.success}</p>}

          <button type="submit" disabled={isAuthenticating}>
            {isAuthenticating ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Log in'}
          </button>
        </form>
      </div>
    </section>
  )
}

export default AuthPage

