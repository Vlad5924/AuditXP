-- AuditXP: Риск-менеджмент. Схема базы данных (PostgreSQL 16)
-- Получена командой pg_dump --schema-only --no-owner auditxp
-- Применение: psql -U auditxp -d auditxp -f db/01_schema.sql
--
-- PostgreSQL database dump
--

\restrict ISe69UEK7JO6YlDcQHqjeSU6OXcbg8RXpoAiT1VEnSpFJKIExB1AIeji6fwawzh

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit_log_protect(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.audit_log_protect() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN RAISE EXCEPTION 'audit_log is append-only (AUD-02)'; END; $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    user_id integer,
    table_name character varying(50) NOT NULL,
    action character varying(50) NOT NULL,
    record_id integer,
    details text,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: audit_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_reports (
    id integer NOT NULL,
    title character varying(200) NOT NULL,
    period_from date NOT NULL,
    period_to date NOT NULL,
    user_id integer NOT NULL,
    status character varying(30) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    submitted_at timestamp without time zone,
    approved_by integer,
    approved_at timestamp without time zone,
    review_comment text,
    signature character varying(64),
    summary jsonb NOT NULL
);


--
-- Name: audit_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_reports_id_seq OWNED BY public.audit_reports.id;


--
-- Name: departments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.departments (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    manager_name character varying(150)
);


--
-- Name: departments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.departments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: departments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.departments_id_seq OWNED BY public.departments.id;


--
-- Name: erp_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.erp_transactions (
    id integer NOT NULL,
    doc_number character varying(50) NOT NULL,
    department_id integer NOT NULL,
    transaction_date timestamp without time zone NOT NULL,
    amount numeric(15,2) NOT NULL,
    counterparty_info character varying(255) NOT NULL,
    account_debit character varying(10),
    account_credit character varying(10),
    batch_id integer,
    imported_at timestamp without time zone NOT NULL
);


--
-- Name: erp_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.erp_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: erp_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.erp_transactions_id_seq OWNED BY public.erp_transactions.id;


--
-- Name: import_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_batches (
    id integer NOT NULL,
    user_id integer,
    source character varying(30) NOT NULL,
    period_from date,
    period_to date,
    started_at timestamp without time zone NOT NULL,
    finished_at timestamp without time zone,
    status character varying(30) NOT NULL,
    rows_total integer NOT NULL,
    rows_loaded integer NOT NULL,
    rows_quarantined integer NOT NULL,
    duplicates integer NOT NULL,
    skipped_existing integer NOT NULL,
    message text
);


--
-- Name: import_batches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.import_batches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: import_batches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.import_batches_id_seq OWNED BY public.import_batches.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    message text NOT NULL,
    is_read boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: quarantine_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quarantine_records (
    id integer NOT NULL,
    batch_id integer NOT NULL,
    doc_number character varying(50),
    reason character varying(255) NOT NULL,
    payload jsonb NOT NULL
);


--
-- Name: quarantine_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quarantine_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quarantine_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quarantine_records_id_seq OWNED BY public.quarantine_records.id;


--
-- Name: risks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.risks (
    id integer NOT NULL,
    report_id integer,
    transaction_id integer NOT NULL,
    user_id integer,
    risk_type character varying(100) NOT NULL,
    description text NOT NULL,
    method character varying(50) NOT NULL,
    anomaly_score numeric(4,3) NOT NULL,
    probability numeric(3,2) NOT NULL,
    impact numeric(15,2) NOT NULL,
    materiality integer NOT NULL,
    level character varying(20) NOT NULL,
    status character varying(30) NOT NULL,
    comment text,
    mitigation_plan text,
    mitigation_owner character varying(150),
    mitigation_due date,
    effectiveness_confirmed boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    escalated_at timestamp without time zone,
    CONSTRAINT ck_risks_probability CHECK (((probability >= (0)::numeric) AND (probability <= (1)::numeric)))
);


--
-- Name: risks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.risks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: risks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.risks_id_seq OWNED BY public.risks.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    permissions jsonb NOT NULL
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    role_id integer NOT NULL,
    login character varying(50) NOT NULL,
    full_name character varying(150) NOT NULL,
    email character varying(150) NOT NULL,
    password_hash character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    is_locked boolean NOT NULL,
    failed_attempts integer NOT NULL,
    reset_token_hash character varying(64),
    reset_token_expires timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    last_login_at timestamp without time zone
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: audit_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_reports ALTER COLUMN id SET DEFAULT nextval('public.audit_reports_id_seq'::regclass);


--
-- Name: departments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments ALTER COLUMN id SET DEFAULT nextval('public.departments_id_seq'::regclass);


--
-- Name: erp_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.erp_transactions ALTER COLUMN id SET DEFAULT nextval('public.erp_transactions_id_seq'::regclass);


--
-- Name: import_batches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batches ALTER COLUMN id SET DEFAULT nextval('public.import_batches_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: quarantine_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_records ALTER COLUMN id SET DEFAULT nextval('public.quarantine_records_id_seq'::regclass);


--
-- Name: risks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks ALTER COLUMN id SET DEFAULT nextval('public.risks_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: audit_reports audit_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_reports
    ADD CONSTRAINT audit_reports_pkey PRIMARY KEY (id);


--
-- Name: departments departments_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_name_key UNIQUE (name);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: erp_transactions erp_transactions_doc_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.erp_transactions
    ADD CONSTRAINT erp_transactions_doc_number_key UNIQUE (doc_number);


--
-- Name: erp_transactions erp_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.erp_transactions
    ADD CONSTRAINT erp_transactions_pkey PRIMARY KEY (id);


--
-- Name: import_batches import_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batches
    ADD CONSTRAINT import_batches_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: quarantine_records quarantine_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_records
    ADD CONSTRAINT quarantine_records_pkey PRIMARY KEY (id);


--
-- Name: risks risks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks
    ADD CONSTRAINT risks_pkey PRIMARY KEY (id);


--
-- Name: risks risks_transaction_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks
    ADD CONSTRAINT risks_transaction_id_key UNIQUE (transaction_id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_login_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_login_key UNIQUE (login);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_created_at ON public.audit_log USING btree (created_at);


--
-- Name: ix_erp_transactions_transaction_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_erp_transactions_transaction_date ON public.erp_transactions USING btree (transaction_date);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_quarantine_records_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quarantine_records_batch_id ON public.quarantine_records USING btree (batch_id);


--
-- Name: ix_risks_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_risks_level ON public.risks USING btree (level);


--
-- Name: ix_risks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_risks_status ON public.risks USING btree (status);


--
-- Name: ix_txn_dept_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_txn_dept_date ON public.erp_transactions USING btree (department_id, transaction_date);


--
-- Name: audit_log trg_audit_log_protect; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_log_protect BEFORE DELETE OR UPDATE ON public.audit_log FOR EACH ROW EXECUTE FUNCTION public.audit_log_protect();


--
-- Name: audit_log audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: audit_reports audit_reports_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_reports
    ADD CONSTRAINT audit_reports_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id);


--
-- Name: audit_reports audit_reports_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_reports
    ADD CONSTRAINT audit_reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: erp_transactions erp_transactions_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.erp_transactions
    ADD CONSTRAINT erp_transactions_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.import_batches(id);


--
-- Name: erp_transactions erp_transactions_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.erp_transactions
    ADD CONSTRAINT erp_transactions_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: import_batches import_batches_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batches
    ADD CONSTRAINT import_batches_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: quarantine_records quarantine_records_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quarantine_records
    ADD CONSTRAINT quarantine_records_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.import_batches(id) ON DELETE CASCADE;


--
-- Name: risks risks_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks
    ADD CONSTRAINT risks_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.audit_reports(id) ON DELETE SET NULL;


--
-- Name: risks risks_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks
    ADD CONSTRAINT risks_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.erp_transactions(id) ON DELETE CASCADE;


--
-- Name: risks risks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.risks
    ADD CONSTRAINT risks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict ISe69UEK7JO6YlDcQHqjeSU6OXcbg8RXpoAiT1VEnSpFJKIExB1AIeji6fwawzh

