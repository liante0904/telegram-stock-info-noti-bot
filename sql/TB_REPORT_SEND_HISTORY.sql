--
-- PostgreSQL database dump
--

\restrict vLQjWQg6gP8Vx5mYc3W6PYkvg7MecBkKNc9OWEWfYdi0p9FLol17lVooY9OeK2u

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
-- Name: TB_REPORT_SEND_HISTORY; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."TB_REPORT_SEND_HISTORY" (
    id integer NOT NULL,
    report_id integer NOT NULL,
    user_id bigint NOT NULL,
    keyword character varying(255),
    sent_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TB_REPORT_SENT_HISTORY_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public."TB_REPORT_SENT_HISTORY_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: TB_REPORT_SENT_HISTORY_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public."TB_REPORT_SENT_HISTORY_id_seq" OWNED BY public."TB_REPORT_SEND_HISTORY".id;


--
-- Name: TB_REPORT_SEND_HISTORY id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_REPORT_SEND_HISTORY" ALTER COLUMN id SET DEFAULT nextval('public."TB_REPORT_SENT_HISTORY_id_seq"'::regclass);


--
-- Name: TB_REPORT_SEND_HISTORY TB_REPORT_SENT_HISTORY_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_REPORT_SEND_HISTORY"
    ADD CONSTRAINT "TB_REPORT_SENT_HISTORY_pkey" PRIMARY KEY (id);


--
-- Name: idx_send_history_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_send_history_report_id ON public."TB_REPORT_SEND_HISTORY" USING btree (report_id);


--
-- Name: idx_send_history_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_send_history_unique ON public."TB_REPORT_SEND_HISTORY" USING btree (report_id, user_id);


--
-- Name: idx_send_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_send_history_user_id ON public."TB_REPORT_SEND_HISTORY" USING btree (user_id);


--
-- Name: TB_REPORT_SEND_HISTORY TB_REPORT_SENT_HISTORY_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TB_REPORT_SEND_HISTORY"
    ADD CONSTRAINT "TB_REPORT_SENT_HISTORY_report_id_fkey" FOREIGN KEY (report_id) REFERENCES public."TB_SEC_REPORTS"(report_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict vLQjWQg6gP8Vx5mYc3W6PYkvg7MecBkKNc9OWEWfYdi0p9FLol17lVooY9OeK2u

