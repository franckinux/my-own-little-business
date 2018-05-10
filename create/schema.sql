CREATE TYPE payedstatusenum AS ENUM (
    'order',
    'payed_by_check',
    'payed_by_paypal',
    'payed_in_cash'
);


CREATE TABLE storage (
    last_invoice_date timestamp without time zone DEFAULT NOW()
);


CREATE TABLE repository (
    id SERIAL PRIMARY KEY NOT NULL,
    name character varying UNIQUE NOT NULL,
    opened boolean DEFAULT TRUE,
    days BOOLEAN ARRAY[7] DEFAULT '{t,t,t,t,t,t,t}'
);


CREATE TABLE client (
    id SERIAL PRIMARY KEY NOT NULL,
    login character varying UNIQUE NOT NULL,
    password_hash character varying NOT NULL,
    confirmed boolean DEFAULT FALSE,
    disabled boolean DEFAULT FALSE,
    super_user boolean DEFAULT FALSE,
    mailing boolean DEFAULT TRUE,
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    email_address character varying UNIQUE NOT NULL,
    phone_number character varying,
    wallet numeric(8,2) DEFAULT 0 CHECK (wallet >= 0),
    created_at timestamp without time zone DEFAULT NOW(),
    last_seen timestamp without time zone,
    repository_id integer REFERENCES repository(id) NOT NULL,
    UNIQUE (first_name, last_name)
);


CREATE TABLE batch (
    id SERIAL PRIMARY KEY NOT NULL,
    date timestamp without time zone UNIQUE NOT NULL,
    opened boolean DEFAULT TRUE
);


CREATE TABLE payment (
    id SERIAL PRIMARY KEY NOT NULL,
    amount numeric(8,2) NOT NULL CHECK (amount != 0),
    date timestamp without time zone DEFAULT NOW(),
    mode payedstatusenum,
    reference character varying,
    client_id integer REFERENCES client(id) NOT NULL
);


CREATE TABLE order_ (
    id SERIAL PRIMARY KEY NOT NULL,
    total numeric(8,2) NOT NULL CHECK (total >= 0),
    date timestamp without time zone DEFAULT NOW(),
    disabled boolean DEFAULT false,
    client_id integer REFERENCES client(id) NOT NULL,
    batch_id integer REFERENCES batch(id) NOT NULL,
    payment_id integer REFERENCES payment(id) DEFAULT NULL
);

CREATE INDEX order_date_index ON order_(date);


CREATE TABLE product (
    id SERIAL PRIMARY KEY NOT NULL,
    name character varying UNIQUE NOT NULL,
    description character varying,
    price numeric(8,2) NOT NULL CHECK (price > 0),
    available boolean DEFAULT TRUE
);


CREATE TABLE batch_product_association (
    quantity integer CHECK (quantity > 0),
    batch_id integer REFERENCES batch(id) NOT NULL,
    product_id integer REFERENCES product(id) NOT NULL,
    PRIMARY KEY (batch_id, product_id)
);

CREATE TABLE order_product_association (
    quantity integer CHECK (quantity > 0),
    order_id integer REFERENCES order_(id) NOT NULL,
    product_id integer REFERENCES product(id) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
