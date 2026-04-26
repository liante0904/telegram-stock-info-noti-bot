--
-- PostgreSQL database dump
--

\restrict ERRqofzhaiaM9HfwMRWnqx2esWTRrE7vNXAxAtfF1fFtdc2elbPnFpXRmLyxBWH

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
-- Name: tbm_sec_reports_telegram_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tbm_sec_reports_telegram_users (
    id bigint NOT NULL,
    first_name character varying,
    last_name character varying,
    username character varying,
    photo_url character varying,
    status character varying,
    created_at bigint
);


--
-- Name: tbm_sec_reports_telegram_users tbm_sec_reports_telegram_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tbm_sec_reports_telegram_users
    ADD CONSTRAINT tbm_sec_reports_telegram_users_pkey PRIMARY KEY (id);


--
-- Name: tbm_sec_reports_telegram_users_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tbm_sec_reports_telegram_users_id_idx ON public.tbm_sec_reports_telegram_users USING btree (id);


--
-- PostgreSQL database dump complete
--

\unrestrict ERRqofzhaiaM9HfwMRWnqx2esWTRrE7vNXAxAtfF1fFtdc2elbPnFpXRmLyxBWH

