import { useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'

const defaultQuizConfig = {
  level: 'intermediate',
  questionCount: 10,
  focus: 'Vocabulary',
}

const normalizeQuestions = (payload) => {
  if (!payload) {
    return []
  }

  if (Array.isArray(payload?.questions)) {
    return payload.questions
  }

  if (Array.isArray(payload)) {
    return payload
  }

  return []
}

const getQuestionId = (question, fallbackIndex) =>
  question?.question_number
    ? `question-${question.question_number}`
    : question?.id ?? question?.questionId ?? `q-${fallbackIndex}`

const getOptions = (question) =>
  question?.choices || question?.answers || question?.options || question?.choicesList || []

const demoUserId = import.meta.env.VITE_DEMO_USER_ID || 'demo-user'

const QuizPage = () => {
  const [config, setConfig] = useState(defaultQuizConfig)
  const [session, setSession] = useState(null)
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [submission, setSubmission] = useState(null)
  const [status, setStatus] = useState({ loading: false, error: null })

  const handleConfigChange = (event) => {
    const { name, value } = event.target
    setConfig((prev) => ({ ...prev, [name]: value }))
  }

  const startQuiz = async (event) => {
    event.preventDefault()
    setStatus({ loading: true, error: null })
    setSubmission(null)

    try {
      const response = await apiClient.startQuiz({
        user_id: demoUserId,
        level: config.level,
        question_count: Number(config.questionCount),
        focus: config.focus,
      })

      const sessionId = response?.session_id ?? response?.sessionId ?? response?.id
      setSession({ ...response, sessionId, focus: config.focus })

      const questionsPayload =
        response?.questions?.length > 0
          ? response
          : await apiClient.fetchQuizQuestions(sessionId)

      const nextQuestions = normalizeQuestions(questionsPayload)
      setQuestions(nextQuestions)
      setAnswers(
        nextQuestions.reduce((acc, question, index) => {
          acc[getQuestionId(question, index)] = ''
          return acc
        }, {}),
      )
    } catch (error) {
      setStatus({ loading: false, error: error.message })
      return
    }

    setStatus({ loading: false, error: null })
  }

  const handleAnswerChange = (questionKey, choiceValue) => {
    setAnswers((prev) => ({ ...prev, [questionKey]: choiceValue }))
  }

  const answeredCount = useMemo(
    () => Object.values(answers).filter((value) => value !== '').length,
    [answers],
  )

  const allAnswered = useMemo(
    () => questions.length > 0 && answeredCount === questions.length,
    [questions.length, answeredCount],
  )

  const submitQuiz = async () => {
    if (!session) {
      return
    }

    setStatus({ loading: true, error: null })

    try {
      const formattedAnswers = questions.map((question, index) => {
        const questionId = getQuestionId(question, index)
        return answers[questionId] ?? ''
      })

      const response = await apiClient.submitQuiz({
        session_id: session.sessionId || session.session_id,
        user_id: demoUserId,
        answers: formattedAnswers,
      })

      setSubmission(response)
    } catch (error) {
      setStatus({ loading: false, error: error.message })
      return
    }

    setStatus({ loading: false, error: null })
  }

  return (
    <section className="quiz-page">
      <header>
        <p className="eyebrow">Adaptive quiz engine</p>
        <h1>Practice TOEFL vocab with AI feedback</h1>
        <p>
          Start a new quiz session to receive adaptive questions from /api/quiz/start,
          /api/quiz/questions, and submit your answers to /api/quiz/submit.
        </p>
      </header>

      <form className="quiz-config" onSubmit={startQuiz}>
        <label>
          <span>Difficulty level</span>
          <select name="level" value={config.level} onChange={handleConfigChange}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>

        <label>
          <span>Number of questions</span>
          <select name="questionCount" value={config.questionCount} onChange={handleConfigChange}>
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={15}>15</option>
          </select>
        </label>

        <label>
          <span>Skill focus</span>
          <select name="focus" value={config.focus} onChange={handleConfigChange}>
            <option value="Vocabulary">Vocabulary</option>
            <option value="Reading">Reading</option>
            <option value="Listening">Listening</option>
            <option value="Speaking">Speaking</option>
          </select>
        </label>

        <button type="submit" disabled={status.loading}>
          {status.loading ? 'Starting session…' : 'Start quiz'}
        </button>
      </form>

      {status.error && <p className="form-feedback error">{status.error}</p>}

      {session && (
        <section className="quiz-session">
          <header>
            <div>
              <p className="eyebrow">Session active</p>
              <h2>{session.level ? `${session.level} level` : 'Custom session'}</h2>
              <p>
                Session ID:{' '}
                <code>{session.sessionId || session.session_id || session.id || 'not provided'}</code>
              </p>
            </div>
            <div className="quiz-progress">
              <p>
                Answered {answeredCount}/{questions.length}
              </p>
              <progress max={questions.length || 1} value={answeredCount} />
            </div>
          </header>

          <ol className="question-list">
            {questions.map((question, index) => {
              const questionId = getQuestionId(question, index)
              const options = getOptions(question)

              return (
                <li key={questionId}>
                  <p className="question-text">{question.prompt || question.text || question.question}</p>
                  <div className="question-meta">
                    <span className="badge">{question.skill || question.topic || 'General'}</span>
                    {question.difficulty && <span className="badge ghost">{question.difficulty}</span>}
                  </div>

                  <div className="choices">
                    {options.map((choice) => {
                      const choiceLabel = choice?.label ?? choice?.text ?? choice
                      const choiceValue = String(choice?.value ?? choice?.id ?? choice)
                      return (
                        <label key={choiceValue}>
                          <input
                            type="radio"
                            name={questionId}
                            value={choiceValue}
                            checked={answers[questionId] === choiceValue}
                            onChange={() => handleAnswerChange(questionId, choiceValue)}
                          />
                          <span>{choiceLabel}</span>
                        </label>
                      )
                    })}
                  </div>
                </li>
              )
            })}
          </ol>

          <footer className="quiz-actions">
            <button type="button" onClick={submitQuiz} disabled={!allAnswered || status.loading}>
              {status.loading ? 'Submitting…' : 'Submit answers'}
            </button>
          </footer>
        </section>
      )}

      {submission && (
        <section className="quiz-results">
          <header>
            <h2>Submission received</h2>
            <p>Review feedback powered by /api/quiz/submit.</p>
          </header>
          <div className="results-grid">
            <article>
              <p className="eyebrow">Score</p>
              <p className="stat-value">
                {submission.score ?? '—'}{' '}
                <span>/ {submission.total_questions ?? (questions.length || '—')}</span>
              </p>
            </article>
            <article>
              <p className="eyebrow">Accuracy</p>
              <p className="stat-value">
                {submission.correct_count && submission.total_questions
                  ? `${Math.round((submission.correct_count / submission.total_questions) * 100)}%`
                  : '—'}
              </p>
            </article>
            <article>
              <p className="eyebrow">Top skill</p>
              <p className="stat-value">{session?.focus ?? 'Vocabulary'}</p>
            </article>
          </div>

          {submission.feedback && (
            <div className="feedback-card">
              <p>{submission.feedback}</p>
            </div>
          )}

          {Array.isArray(submission.recommendations) && submission.recommendations.length > 0 && (
            <ul className="recommendations">
              {submission.recommendations.map((item, index) => (
                <li key={item.id ?? index}>
                  <span className="badge ghost">{item.skill || 'Tip'}</span>
                  <p>{item.text || item.summary || item}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </section>
  )
}

export default QuizPage

