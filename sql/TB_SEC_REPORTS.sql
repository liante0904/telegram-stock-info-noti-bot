--
-- PostgreSQL database dump
--

\restrict tj6WfPW1u4T2DqMnf3b5IJ7JH9lZZtWBNBxay18N6jerYkMXeZ7tE8i7zpaHuX2

-- Dumped from database version 15.17
-- Dumped by pg_dump version 15.17

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: TB_SEC_REPORTS; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."TB_SEC_REPORTS" (
    report_id bigint NOT NULL,
    "sec_firm_order" integer,
    "article_board_order" integer,
    "FIRM_NM" text,
    "ARTICLE_TITLE" text,
    "ARTICLE_URL" text,
    "MAIN_CH_SEND_YN" text,
    "DOWNLOAD_STATUS_YN" text DEFAULT ''::text,
    "DOWNLOAD_URL" text,
    "SAVE_TIME" text,
    "REG_DT" text DEFAULT ''::text,
    "WRITER" text DEFAULT ''::text,
    "KEY" text,
    "TELEGRAM_URL" text DEFAULT ''::text,
    "MKT_TP" text DEFAULT 'KR'::text,
    "GEMINI_SUMMARY" text,
    "SUMMARY_TIME" text,
    "SUMMARY_MODEL" text,
    "ARCHIVE_PATH" text,
    retry_count integer DEFAULT 0,
    sync_status integer DEFAULT 0,
    "PDF_URL" text DEFAULT ''::text,
    "ATTACH_URL" text
);


--
-- Name: COLUMN "TB_SEC_REPORTS"."ATTACH_URL"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."TB_SEC_REPORTS"."ATTACH_URL" IS 'ATTACH_URL';


--
-- Name: tb_sec_reports_report_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tb_sec_reports_report_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tb_sec_reports_report_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tb_sec_reports_report_id_seq OWNED BY public."TB_SEC_REPORTS".report_id;


--
-- Name: TB_SEC_REPORTS report_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_SEC_REPORTS" ALTER COLUMN report_id SET DEFAULT nextval('public.tb_sec_reports_report_id_seq'::regclass);


--
-- Name: TB_SEC_REPORTS TB_SEC_REPORTS_KEY_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_SEC_REPORTS"
    ADD CONSTRAINT "TB_SEC_REPORTS_KEY_key" UNIQUE ("KEY");


--
-- Name: TB_SEC_REPORTS TB_SEC_REPORTS_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_SEC_REPORTS"
    ADD CONSTRAINT "TB_SEC_REPORTS_pkey" PRIMARY KEY (report_id);


--
-- Name: idx_tb_sec_reports_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tb_sec_reports_key ON public."TB_SEC_REPORTS" USING btree ("KEY");


--
-- Name: idx_tb_sec_reports_reg_dt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tb_sec_reports_reg_dt ON public."TB_SEC_REPORTS" USING btree ("REG_DT");


--
-- Name: idx_tb_sec_reports_reg_dt_sec_firm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tb_sec_reports_reg_dt_sec_firm ON public."TB_SEC_REPORTS" USING btree ("REG_DT" DESC, "sec_firm_order");


--
-- Name: idx_tb_sec_reports_save_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tb_sec_reports_save_time ON public."TB_SEC_REPORTS" USING btree ("SAVE_TIME");


--
-- Name: idx_tb_sec_reports_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tb_sec_reports_search ON public."TB_SEC_REPORTS" USING btree ("FIRM_NM", "ARTICLE_TITLE", "WRITER");


--
-- Name: TB_SEC_REPORTS trg_set_ds_share_telegram_url; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_ds_share_telegram_url BEFORE INSERT OR UPDATE ON public."TB_SEC_REPORTS" FOR EACH ROW EXECUTE FUNCTION public.set_ds_share_telegram_url();


--
-- PostgreSQL database dump complete
--

\unrestrict tj6WfPW1u4T2DqMnf3b5IJ7JH9lZZtWBNBxay18N6jerYkMXeZ7tE8i7zpaHuX2

