--
-- PostgreSQL database dump
--

\restrict gKUtuGxZ5OI0y2mhsdKt86SWiTJJ7ueNckXE4jXY00s6eCqNPdr5Vv1JHFbm4dv

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
-- Name: TBM_SEC_FIRM_BOARD_INFO; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."TBM_SEC_FIRM_BOARD_INFO" (
    "SEC_FIRM_ORDER" integer NOT NULL,
    "ARTICLE_BOARD_ORDER" integer NOT NULL,
    "BOARD_NM" text,
    "BOARD_CD" text,
    "LABEL_NM" text
);


--
-- Name: TBM_SEC_FIRM_BOARD_INFO TBM_SEC_FIRM_BOARD_INFO_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TBM_SEC_FIRM_BOARD_INFO"
    ADD CONSTRAINT "TBM_SEC_FIRM_BOARD_INFO_pkey" PRIMARY KEY ("SEC_FIRM_ORDER", "ARTICLE_BOARD_ORDER");


--
-- Name: TBM_SEC_FIRM_BOARD_INFO TBM_SEC_FIRM_BOARD_INFO_SEC_FIRM_ORDER_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."TBM_SEC_FIRM_BOARD_INFO"
    ADD CONSTRAINT "TBM_SEC_FIRM_BOARD_INFO_SEC_FIRM_ORDER_fkey" FOREIGN KEY ("SEC_FIRM_ORDER") REFERENCES public."TBM_SEC_FIRM_INFO"("SEC_FIRM_ORDER");


--
-- PostgreSQL database dump complete
--

\unrestrict gKUtuGxZ5OI0y2mhsdKt86SWiTJJ7ueNckXE4jXY00s6eCqNPdr5Vv1JHFbm4dv

