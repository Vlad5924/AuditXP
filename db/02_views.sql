-- AuditXP: Риск-менеджмент. Аналитические представления (PostgreSQL 14+)
-- Применение после создания схемы
--   psql -h localhost -U auditxp -d auditxp -f db/02_views.sql

-- Тепловая карта 5x5 по месяцам (классы вероятности и ущерба, правило BR-5)
CREATE OR REPLACE VIEW v_risk_heatmap AS
SELECT date_trunc('month', t.transaction_date)::date AS period_month,
       LEAST(5, floor(LEAST(GREATEST(r.probability, 0), 1) * 5)::int + 1)
           AS probability_class,
       1 + (abs(r.impact) >= 10000)::int + (abs(r.impact) >= 100000)::int
         + (abs(r.impact) >= 500000)::int + (abs(r.impact) >= 1000000)::int
           AS damage_class,
       count(*) AS risks_count,
       sum(abs(r.impact)) AS impact_total
FROM risks r
JOIN erp_transactions t ON t.id = r.transaction_id
GROUP BY 1, 2, 3;

-- Аномалии по подразделениям за месяц
CREATE OR REPLACE VIEW v_department_anomalies AS
SELECT date_trunc('month', t.transaction_date)::date AS period_month,
       d.name AS department,
       count(*) AS risks_count,
       count(*) FILTER (WHERE r.level = 'Критический') AS critical_count,
       round(avg(r.anomaly_score), 3) AS avg_score,
       sum(abs(r.impact)) AS impact_total
FROM risks r
JOIN erp_transactions t ON t.id = r.transaction_id
JOIN departments d ON d.id = t.department_id
GROUP BY 1, 2;

-- Результативность аудиторов (обработанные и закрытые риски)
CREATE OR REPLACE VIEW v_auditor_performance AS
SELECT u.full_name AS auditor,
       count(r.id) AS risks_total,
       count(r.id) FILTER (WHERE r.status = 'Закрыт') AS risks_closed,
       count(r.id) FILTER (WHERE r.status IN ('Выявлен', 'Оценен',
           'Подтвержден', 'В проработке')) AS risks_open,
       count(r.id) FILTER (WHERE r.escalated_at IS NOT NULL)
           AS risks_escalated
FROM users u
JOIN roles ro ON ro.id = u.role_id AND ro.name = 'Аудитор'
LEFT JOIN risks r ON r.user_id = u.id
GROUP BY u.full_name;
