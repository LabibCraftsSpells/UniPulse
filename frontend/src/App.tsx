import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'

/**
 * App root — sets up client-side routing.
 *
 * KEY CONCEPT: Client-Side Routing
 * ----------------------------------
 * In a traditional website, clicking a link sends a new request to the server.
 * With React Router, navigation happens WITHOUT reloading the page.
 * The URL changes, but React just swaps which component is shown.
 *
 * Routes:
 *   /           → LandingPage (connect Gmail)
 *   /dashboard  → DashboardPage (after auth)
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
