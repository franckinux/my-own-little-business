First migration
---------------

Fields creation : ::

    ALTER TABLE product ADD name_lang1 character varying;
    ALTER TABLE product ADD description_lang1 character varying;

Update all records name fields.

Add contraints to name field: ::

    ALTER TABLE product ALTER COLUMN name_lang1 SET NOT NULL;
    ALTER TABLE product ADD CONSTRAINT product_name_lang1_key UNIQUE (name_lang1);

