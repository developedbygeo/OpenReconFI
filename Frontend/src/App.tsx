import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/AppShell.tsx'
import { InvoiceListPage, InvoiceDetailPage } from './features/invoices/index.tsx'
import { CollectionPage } from './features/collection/index.tsx'
import { StatementUploadPage, MatchReviewPage, ReconciliationOverviewPage, ManualMatchPage } from './features/reconciliation/index.tsx'
import { VendorListPage, VendorDetailPage, VendorFormPage } from './features/vendors/index.tsx'
import { DashboardPage } from './features/dashboard/index.tsx'
import { ReportsPage } from './features/reports/index.tsx'
import { ChatPage } from './features/chat/index.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/invoices" element={<InvoiceListPage />} />
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
          <Route path="/collection" element={<CollectionPage />} />
          <Route path="/reconciliation" element={<StatementUploadPage />} />
          <Route path="/reconciliation/overview" element={<ReconciliationOverviewPage />} />
          <Route path="/reconciliation/manual-match" element={<ManualMatchPage />} />
          <Route path="/reconciliation/matches" element={<MatchReviewPage />} />
          <Route path="/vendors" element={<VendorListPage />} />
          <Route path="/vendors/new" element={<VendorFormPage />} />
          <Route path="/vendors/:id" element={<VendorDetailPage />} />
          <Route path="/vendors/:id/edit" element={<VendorFormPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
