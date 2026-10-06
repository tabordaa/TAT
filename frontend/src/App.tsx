import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { EmployeesPage } from './pages/EmployeesPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterEmployeePage } from './pages/RegisterEmployeePage'

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/empleados" element={<EmployeesPage />} />
              <Route path="/empleados/nuevo" element={<RegisterEmployeePage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
