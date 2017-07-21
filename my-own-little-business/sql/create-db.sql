--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.3
-- Dumped by pg_dump version 9.6.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner:
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: payedstatusenum; Type: TYPE; Schema: public
--

CREATE TYPE payedstatusenum AS ENUM (
    'not_payed',
    'payed_by_check',
    'payed_inline'
);


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: batch; Type: TABLE; Schema: public
--

CREATE TABLE batch (
    id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    capacity integer NOT NULL,
    opened boolean DEFAULT TRUE
);


--
-- Name: batch_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE batch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE batch_id_seq OWNED BY batch.id;


--
-- Name: client; Type: TABLE; Schema: public
--

CREATE TABLE client (
    id integer NOT NULL,
    login character varying NOT NULL,
    password_hash character varying NOT NULL,
    confirmed boolean DEFAULT FALSE,
    disabled boolean DEFAULT FALSE,
    super_user boolean DEFAULT FALSE,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    email_address character varying NOT NULL,
    phone_number character varying,
    wallet numeric(8,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT NOW(),
    last_seen timestamp without time zone,
    repository_id integer
);


--
-- Name: client_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE client_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: client_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE client_id_seq OWNED BY client.id;


--
-- Name: order_; Type: TABLE; Schema: public
--

CREATE TABLE order_ (
    id integer NOT NULL,
    placed_at timestamp without time zone DEFAULT NOW(),
    client_id integer NOT NULL,
    batch_id integer NOT NULL,
    payment_id integer DEFAULT NULL
);


--
-- Name: order__id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE order__id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order__id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE order__id_seq OWNED BY order_.id;


--
-- Name: order_product_association; Type: TABLE; Schema: public
--

CREATE TABLE order_product_association (
    quantity integer,
    order_id integer NOT NULL,
    product_id integer NOT NULL
);


--
-- Name: payment; Type: TABLE; Schema: public
--

CREATE TABLE payment (
    id integer NOT NULL,
    total numeric(8,2) NOT NULL,
    payed_at timestamp without time zone DEFAULT NOW(),
    mode payedstatusenum DEFAULT 'not_payed',
    reference character varying
);


--
-- Name: payment_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE payment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE payment_id_seq OWNED BY payment.id;


--
-- Name: product; Type: TABLE; Schema: public
--

CREATE TABLE product (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying,
    price numeric(8,2) NOT NULL,
    load numeric(8,2) DEFAULT 1,
    available boolean DEFAULT TRUE
);


--
-- Name: product_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE product_id_seq OWNED BY product.id;


--
-- Name: repository; Type: TABLE; Schema: public
--

CREATE TABLE repository (
    id integer NOT NULL,
    name character varying NOT NULL,
    opened boolean DEFAULT TRUE
);


--
-- Name: repository_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE repository_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: repository_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE repository_id_seq OWNED BY repository.id;


--
-- Name: batch id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY batch ALTER COLUMN id SET DEFAULT nextval('batch_id_seq'::regclass);


--
-- Name: client id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY client ALTER COLUMN id SET DEFAULT nextval('client_id_seq'::regclass);


--
-- Name: order_ id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY order_ ALTER COLUMN id SET DEFAULT nextval('order__id_seq'::regclass);


--
-- Name: payment id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY payment ALTER COLUMN id SET DEFAULT nextval('payment_id_seq'::regclass);


--
-- Name: product id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY product ALTER COLUMN id SET DEFAULT nextval('product_id_seq'::regclass);


--
-- Name: repository id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY repository ALTER COLUMN id SET DEFAULT nextval('repository_id_seq'::regclass);


--
-- Name: batch batch_date_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY batch
    ADD CONSTRAINT batch_date_key UNIQUE (date);


--
-- Name: batch batch_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY batch
    ADD CONSTRAINT batch_pkey PRIMARY KEY (id);


--
-- Name: client client_email_address_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY client
    ADD CONSTRAINT client_email_address_key UNIQUE (email_address);


--
-- Name: client client_login_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY client
    ADD CONSTRAINT client_login_key UNIQUE (login);


--
-- Name: client client_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY client
    ADD CONSTRAINT client_pkey PRIMARY KEY (id);


--
-- Name: order_ order__pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_
    ADD CONSTRAINT order__pkey PRIMARY KEY (id);


--
-- Name: order_product_association order_product_association_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_product_association
    ADD CONSTRAINT order_product_association_pkey PRIMARY KEY (order_id, product_id);


--
-- Name: payment payment_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY payment
    ADD CONSTRAINT payment_pkey PRIMARY KEY (id);


--
-- Name: product product_name_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY product
    ADD CONSTRAINT product_name_key UNIQUE (name);


--
-- Name: product product_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- Name: repository repository_name_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY repository
    ADD CONSTRAINT repository_name_key UNIQUE (name);


--
-- Name: repository repository_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY repository
    ADD CONSTRAINT repository_pkey PRIMARY KEY (id);


--
-- Name: client client_repository_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY client
    ADD CONSTRAINT client_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES repository(id);


--
-- Name: order_ order__batch_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_
    ADD CONSTRAINT order__batch_id_fkey FOREIGN KEY (batch_id) REFERENCES batch(id);


--
-- Name: order_ order__client_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_
    ADD CONSTRAINT order__client_id_fkey FOREIGN KEY (client_id) REFERENCES client(id);


--
-- Name: order_ order__payment_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_
    ADD CONSTRAINT order__payment_id_fkey FOREIGN KEY (payment_id) REFERENCES payment(id);


--
-- Name: order_product_association order_product_association_order_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_product_association
    ADD CONSTRAINT order_product_association_order_id_fkey FOREIGN KEY (order_id) REFERENCES order_(id);


--
-- Name: order_product_association order_product_association_product_id_fkey; Type: FK CONSTRAINT; Schema: public
--

ALTER TABLE ONLY order_product_association
    ADD CONSTRAINT order_product_association_product_id_fkey FOREIGN KEY (product_id) REFERENCES product(id);


--
-- PostgreSQL database dump complete
--
