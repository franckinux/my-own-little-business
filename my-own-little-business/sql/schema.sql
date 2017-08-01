CREATE TYPE payedstatusenum AS ENUM (
    'not_payed',
    'payed_by_check',
    'payed_inline'
);


CREATE TABLE repository (
    id SERIAL PRIMARY KEY NOT NULL,
    name character varying UNIQUE NOT NULL,
    opened boolean DEFAULT TRUE
);


CREATE TABLE client (
    id SERIAL PRIMARY KEY NOT NULL,
    login character varying UNIQUE NOT NULL,
    password_hash character varying NOT NULL,
    confirmed boolean DEFAULT FALSE,
    disabled boolean DEFAULT FALSE,
    super_user boolean DEFAULT FALSE,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    email_address character varying UNIQUE NOT NULL,
    phone_number character varying,
    wallet numeric(8,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT NOW(),
    last_seen timestamp without time zone,
    repository_id integer REFERENCES repository(id),
    UNIQUE (first_name, last_name)
);


CREATE TABLE batch (
    id SERIAL PRIMARY KEY NOT NULL,
    date timestamp without time zone UNIQUE NOT NULL,
    capacity integer NOT NULL,
    opened boolean DEFAULT TRUE
);


CREATE TABLE payment (
    id SERIAL PRIMARY KEY NOT NULL,
    total numeric(8,2) NOT NULL,
    claimed_at timestamp without time zone DEFAULT NOW(),
    payed_at timestamp without time zone DEFAULT NULL,
    mode payedstatusenum DEFAULT 'not_payed',
    reference character varying
);


CREATE TABLE order_ (
    id SERIAL PRIMARY KEY NOT NULL,
    total numeric(8,2) NOT NULL,
    placed_at timestamp without time zone DEFAULT NOW(),
    client_id integer REFERENCES client(id) NOT NULL,
    batch_id integer REFERENCES batch(id) NOT NULL,
    payment_id integer REFERENCES payment(id) DEFAULT NULL
);


CREATE TABLE product (
    id SERIAL PRIMARY KEY NOT NULL,
    name character varying UNIQUE NOT NULL,
    description character varying,
    price numeric(8,2) NOT NULL,
    load numeric(8,2) DEFAULT 1,
    available boolean DEFAULT TRUE
);


CREATE TABLE order_product_association (
    quantity integer,
    order_id integer REFERENCES order_(id) NOT NULL,
    product_id integer REFERENCES product(id) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
