-- Table: public.User_Logs

DROP TABLE IF EXISTS public."User_Logs";

CREATE TABLE IF NOT EXISTS public."User_Logs"
(
    "ID" bigint NOT NULL,
    "User_ID" bigint NOT NULL,
    "Module" text COLLATE pg_catalog."default" NOT NULL,
    "Action" text COLLATE pg_catalog."default",
    "Result" text COLLATE pg_catalog."default",
    "Details" text COLLATE pg_catalog."default",
    CONSTRAINT "ID" PRIMARY KEY ("ID"),
    CONSTRAINT "User_Logs_UserDetails" FOREIGN KEY ("User_ID")
        REFERENCES public."User_Details" ("ID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."User_Logs"
    OWNER to mscds;
-- Index: fki_User_Logs_UserDetails

-- DROP INDEX IF EXISTS public."fki_User_Logs_UserDetails";

CREATE INDEX IF NOT EXISTS "fki_User_Logs_UserDetails"
    ON public."User_Logs" USING btree
    ("User_ID" ASC NULLS LAST)
    TABLESPACE pg_default;