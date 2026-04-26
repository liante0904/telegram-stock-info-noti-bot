--
-- PostgreSQL database dump
--

\restrict uXIseld0awamIcfVDMjM3wrBTmdkofGNsJifWbVOEwZz9aQI47wlvNJyIiHwotS

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
-- Name: tbm_sec_reports_alert_keywords; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tbm_sec_reports_alert_keywords (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    keyword text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: tbm_sec_reports_alert_keywords_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tbm_sec_reports_alert_keywords_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tbm_sec_reports_alert_keywords_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tbm_sec_reports_alert_keywords_id_seq OWNED BY public.tbm_sec_reports_alert_keywords.id;


--
-- Name: tbm_sec_reports_alert_keywords id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbm_sec_reports_alert_keywords ALTER COLUMN id SET DEFAULT nextval('public.tbm_sec_reports_alert_keywords_id_seq'::regclass);


--
-- Name: tbm_sec_reports_alert_keywords tbm_sec_reports_alert_keywords_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbm_sec_reports_alert_keywords
    ADD CONSTRAINT tbm_sec_reports_alert_keywords_pkey PRIMARY KEY (id);


--
-- Name: tbm_sec_reports_alert_keywords tbm_sec_reports_alert_keywords_user_id_keyword_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbm_sec_reports_alert_keywords
    ADD CONSTRAINT tbm_sec_reports_alert_keywords_user_id_keyword_key UNIQUE (user_id, keyword);


--
-- PostgreSQL database dump complete
--

\unrestrict uXIseld0awamIcfVDMjM3wrBTmdkofGNsJifWbVOEwZz9aQI47wlvNJyIiHwotS

