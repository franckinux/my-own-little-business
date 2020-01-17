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
    created_at timestamp without time zone DEFAULT NOW(),
    last_seen timestamp without time zone,
    repository_id integer REFERENCES repository(id) NOT NULL,
    UNIQUE (first_name, last_name)
);


CREATE TABLE batch (
    id SERIAL PRIMARY KEY NOT NULL,
    date timestamp without time zone UNIQUE NOT NULL,
    capacity numeric(4,2) NOT NULL CHECK (capacity > 0),
    opened boolean DEFAULT TRUE
);

CREATE INDEX batch_date_index ON batch(date);


CREATE TABLE order_ (
    id SERIAL PRIMARY KEY NOT NULL,
    total numeric(8,2) NOT NULL CHECK (total >= 0),
    date timestamp without time zone DEFAULT NOW(),
    disabled boolean DEFAULT false,
    client_id integer REFERENCES client(id) NOT NULL,
    batch_id integer REFERENCES batch(id) NOT NULL
);

CREATE INDEX order_date_index ON order_(date);


CREATE TABLE product (
    id SERIAL PRIMARY KEY NOT NULL,
    name character varying UNIQUE NOT NULL,
    name_lang1 character varying UNIQUE NOT NULL,
    description character varying,
    description_lang1 character varying,
    load numeric(8,2) NOT NULL CHECK (load != 0),
    price numeric(8,2) NOT NULL CHECK (price > 0),
    available boolean DEFAULT TRUE
);


CREATE TABLE order_product_association (
    quantity integer CHECK (quantity > 0),
    order_id integer REFERENCES order_(id) NOT NULL,
    product_id integer REFERENCES product(id) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
