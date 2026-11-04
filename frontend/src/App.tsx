import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider'
import { CHANGE_PASSWORD_PATH, ProtectedRoute } from './auth/ProtectedRoute'
import { RoleRoute } from './auth/RoleRoute'
import { AppLayout } from './layouts/AppLayout'
import { AuditPage } from './pages/AuditPage'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { DashboardPage } from './pages/DashboardPage'
import { EmployeeDetailPage } from './pages/EmployeeDetailPage'
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
            <Route path={CHANGE_PASSWORD_PATH} element={<ChangePasswordPage />} />
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/empleados" element={<EmployeesPage />} />
              <Route path="/empleados/nuevo" element={<RegisterEmployeePage />} />
              <Route path="/empleados/:employeeId" element={<EmployeeDetailPage />} />
              <Route element={<RoleRoute allowed={['ADMIN']} />}>
                <Route path="/auditoria" element={<AuditPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
