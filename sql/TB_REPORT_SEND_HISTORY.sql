--
-- PostgreSQL database dump
--

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
-- Name: tbl_report_send_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tbl_report_send_history (
    id integer NOT NULL,
    report_id bigint NOT NULL,
    user_id text NOT NULL,
    keyword text,
    sent_at timestamp with time zone DEFAULT now()
);


--
-- Name: tbl_report_send_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tbl_report_send_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tbl_report_send_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tbl_report_send_history_id_seq OWNED BY public.tbl_report_send_history.id;


--
-- Name: tbl_report_send_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbl_report_send_history ALTER COLUMN id SET DEFAULT nextval('public.tbl_report_send_history_id_seq'::regclass);


--
-- Name: tbl_report_send_history tbl_report_send_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbl_report_send_history
    ADD CONSTRAINT tbl_report_send_history_pkey PRIMARY KEY (id);


--
-- Name: idx_send_history_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_send_history_report_id ON public.tbl_report_send_history USING btree (report_id);


--
-- Name: idx_send_history_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_send_history_unique ON public.tbl_report_send_history USING btree (report_id, user_id);


--
-- Name: idx_send_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_send_history_user_id ON public.tbl_report_send_history USING btree (user_id);


--
-- Name: tbl_report_send_history tbl_report_send_history_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbl_report_send_history
    ADD CONSTRAINT tbl_report_send_history_report_id_fkey FOREIGN KEY (report_id) REFERENCES public.tbl_sec_reports(report_id) ON DELETE CASCADE;
