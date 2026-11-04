// Типы данных REST API AuditXP
export type Role = "Аудитор" | "Руководитель" | "Администратор";
export type Zone = "green" | "yellow" | "orange" | "red";

export interface User {
  id: number;
  login: string;
  full_name: string;
  email: string;
  role_name: Role;
  is_active: boolean;
  is_locked: boolean;
  failed_attempts: number;
  last_login_at: string | null;
}

export interface Transaction {
  id: number;
  doc_number: string;
  transaction_date: string;
  amount: number;
  counterparty_info: string;
  department: string;
  account_debit: string | null;
  account_credit: string | null;
}

export interface RiskAction {
  action: string;
  title: string;
}

export interface Risk {
  id: number;
  code: string;
  risk_type: string;
  description: string;
  method: string;
  anomaly_score: number;
  probability: number;
  impact: number;
  materiality: number;
  level: string;
  zone: Zone;
  status: string;
  comment: string | null;
  mitigation_plan: string | null;
  mitigation_owner: string | null;
  mitigation_due: string | null;
  effectiveness_confirmed: boolean;
  created_at: string;
  escalated_at: string | null;
  actions: RiskAction[];
  transaction: Transaction;
}

export interface Period {
  date_from: string;
  date_to: string;
}

export interface Overview {
  period_from: string;
  period_to: string;
  transactions: number;
  risks: number;
  critical: number;
  levels: Record<string, number>;
  processed: number;
  processed_pct: number;
  priority: Risk[];
  departments: { name: string; count: number; share: number }[];
  weekly: { label: string; count: number }[];
  last_import: string | null;
}

export interface HeatCell {
  count: number;
  impact: number;
  score: number;
  zone: Zone;
}

export interface Heatmap {
  probability_labels: string[];
  damage_labels: string[];
  cells: HeatCell[][];
  total: number;
  escalation_score: number;
  top: { id: number; code: string; risk_type: string; materiality: number;
         level: string; impact: number }[];
}

export interface ReportSummary {
  transactions: number;
  risks: number;
  critical: number;
  processed: number;
  total_impact: number;
  levels: Record<string, number>;
  departments: [string, number][];
  heatmap?: Heatmap;
}

export interface Report {
  id: number;
  title: string;
  period_from: string;
  period_to: string;
  status: string;
  created_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  author: string;
  approver: string | null;
  review_comment: string | null;
  signature: string | null;
  summary: ReportSummary;
}

export interface ImportBatch {
  id: number;
  source: string;
  status: string;
  period_from: string | null;
  period_to: string | null;
  started_at: string;
  finished_at: string | null;
  rows_total: number;
  rows_loaded: number;
  rows_quarantined: number;
  duplicates: number;
  skipped_existing: number;
  message: string | null;
  user: string;
}

export type MappingState = "ok" | "warning" | "missing";

export interface MappingSuggestion {
  source: string;
  target: string | null;
  status: MappingState;
}

export interface Preview {
  headers: string[];
  suggestions: MappingSuggestion[];
  rows: Record<string, string | number | null>[];
  stats: { total: number; clean: number; quarantined: number;
           duplicates: number };
}

export interface ImportResult {
  batch_id: number;
  status: string;
  rows_total: number;
  rows_loaded: number;
  rows_quarantined: number;
  duplicates: number;
  skipped_existing: number;
  duration_s: number;
  message: string;
  period_from?: string | null;
  period_to?: string | null;
}

export interface DetectionResult {
  transactions: number;
  risks_created: number;
  skipped_existing: number;
  critical: number;
  method: string;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  user: string;
  table_name: string;
  action: string;
  record_id: number | null;
  details: string | null;
}

export interface NotificationItem {
  id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}
