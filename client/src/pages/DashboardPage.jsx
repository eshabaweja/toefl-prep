import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuth } from '../context/AuthContext'

const normalizeLessons = (lessonPlan) => {
  if (!lessonPlan) {
    return []
  }

  if (Array.isArray(lessonPlan)) {
    return lessonPlan
  }

  if (Array.isArray(lessonPlan?.lessons)) {
    return lessonPlan.lessons
  }

  if (lessonPlan?.plan && Array.isArray(lessonPlan.plan)) {
    return lessonPlan.plan
  }

  if (lessonPlan?.sections && Array.isArray(lessonPlan.sections)) {
    return lessonPlan.sections
  }

  return Object.values(lessonPlan).filter((entry) => typeof entry === 'object')
}

const DashboardPage = () => {
  const { token, user } = useAuth()
  const [dashboardData, setDashboardData] = useState(null)
  const [lessonPlan, setLessonPlan] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchAllData = useCallback(async () => {
    if (!token) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const [dashboardResponse, lessonPlanResponse] = await Promise.all([
        apiClient.getDashboard(token),
        apiClient.getLessonPlan(token),
      ])

      setDashboardData(dashboardResponse)
      setLessonPlan(normalizeLessons(lessonPlanResponse))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchAllData()
  }, [fetchAllData])

  const stats = useMemo(() => {
    const summary = dashboardData?.summary || dashboardData
    return [
      {
        label: 'Current score',
        value: summary?.currentScore ?? '—',
      },
      {
        label: 'Target score',
        value: summary?.targetScore ?? user?.targetScore ?? '—',
      },
      {
        label: 'Words mastered',
        value: summary?.wordsMastered ?? summary?.words ?? '—',
      },
      {
        label: 'Practice streak',
        value: summary?.streakDays ? `${summary.streakDays} days` : '0 days',
      },
    ]
  }, [dashboardData, user])

  return (
    <section className="dashboard-page">
      <header className="dashboard-hero">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h1>{user?.fullName || user?.name || 'TOEFL learner'}</h1>
          <p>
            Track your AI-assisted lesson plan, stay on top of quiz sessions, and monitor your TOEFL
            progress in one place.
          </p>
        </div>

        <div className="hero-actions">
          <button type="button" onClick={fetchAllData} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh data'}
          </button>
        </div>
      </header>

      {error && <p className="form-feedback error">{error}</p>}

      <section className="stats-grid">
        {stats.map((stat) => (
          <article key={stat.label}>
            <p className="eyebrow">{stat.label}</p>
            <p className="stat-value">{stat.value}</p>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article>
          <header>
            <h2>Lesson plan</h2>
            <p>Synced from /api/lesson-plan.</p>
          </header>

          {loading && !lessonPlan.length && <p className="muted">Loading your plan…</p>}
          {!loading && !lessonPlan.length && (
            <p className="muted">No lesson plan yet. Start a quiz session to generate one.</p>
          )}

          <ol className="lesson-plan">
            {lessonPlan.map((lesson, index) => (
              <li key={lesson.id ?? lesson.title ?? index}>
                <div>
                  <p className="lesson-title">{lesson.title || `Task ${index + 1}`}</p>
                  <p className="lesson-meta">{lesson.skill || lesson.focus || 'General'}</p>
                </div>
                <div className="lesson-status">
                  <span className={`badge ${lesson.status || 'pending'}`}>{lesson.status || 'pending'}</span>
                  {lesson.nextAction && <p className="lesson-next">Next: {lesson.nextAction}</p>}
                </div>
              </li>
            ))}
          </ol>
        </article>

        <article>
          <header>
            <h2>Recent quiz session</h2>
            <p>Automatically updated from /api/quiz/start and /api/quiz/submit responses.</p>
          </header>

          {dashboardData?.latestQuiz ? (
            <div className="quiz-summary">
              <p className="quiz-score">
                {dashboardData.latestQuiz.score ?? '—'}{' '}
                <span> / {dashboardData.latestQuiz.total ?? 120}</span>
              </p>
              <ul>
                <li>Level: {dashboardData.latestQuiz.level ?? '—'}</li>
                <li>Duration: {dashboardData.latestQuiz.duration ?? '—'}</li>
                <li>Strength: {dashboardData.latestQuiz.strength ?? '—'}</li>
                <li>Focus: {dashboardData.latestQuiz.focus ?? 'Vocabulary'}</li>
              </ul>
              <p className="muted">
                Keep practicing to improve your accuracy and unlock harder question sets.
              </p>
            </div>
          ) : (
            <p className="muted">Complete a quiz to see detailed analytics here.</p>
          )}
        </article>
      </section>
    </section>
  )
}

export default DashboardPage

