import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import { App } from './App'
import { PlannerPage } from './pages/PlannerPage'
import { HistoryPage } from './pages/HistoryPage'
import { ItineraryGenerationPage } from './pages/ItineraryGenerationPage'
import { ItineraryPage } from './pages/ItineraryPage'
import { SettingsPage } from './pages/SettingsPage'
import { DestinationsPage } from './pages/DestinationsPage'
import { WorldPage } from './pages/WorldPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <PlannerPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'destinations', element: <DestinationsPage /> },
      { path: 'world', element: <WorldPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'itinerary/new', element: <ItineraryGenerationPage /> },
      { path: 'itinerary/:id', element: <ItineraryPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
