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
-- Name: tbm_sec_firm_info; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tbm_sec_firm_info (
    sec_firm_order integer NOT NULL,
    firm_nm text NOT NULL,
    telegram_update_yn text DEFAULT 'N'::text,
    comment_pdf_url text
);


--
-- Name: tbm_sec_firm_info tbm_sec_firm_info_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbm_sec_firm_info
    ADD CONSTRAINT tbm_sec_firm_info_pkey PRIMARY KEY (sec_firm_order);
