const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

const buildUrl = (path) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

const request = async (path, { method = 'GET', token, body } = {}) => {
  const headers = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(buildUrl(path), {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  })

  const text = await response.text()
  let data

  if (text) {
    try {
      data = JSON.parse(text)
    } catch (error) {
      console.warn('Unable to parse JSON response', error)
    }
  }

  if (!response.ok) {
    const message = data?.message || `Request failed with status ${response.status}`
    throw new Error(message)
  }

  return data
}

export const apiClient = {
  signup: (payload) => request('/api/signup', { method: 'POST', body: payload }),
  login: (payload) => request('/api/login', { method: 'POST', body: payload }),
  logout: (token) => request('/api/logout', { method: 'POST', token }),
  startQuiz: (payload) =>
    request('/api/quiz/start', {
      method: 'POST',
      body: payload,
    }),
  fetchQuizQuestions: (sessionId) => request(`/api/quiz/questions/${sessionId}`),
  submitQuiz: (payload) =>
    request('/api/quiz/submit', {
      method: 'POST',
      body: payload,
    }),
  getDashboard: (userId) => request(`/api/dashboard/${userId}`),
  getLessonPlan: (token) => request('/api/lesson-plan', { token }),
}

export default apiClient

