-- Table: public.User_RegRequests

DROP TABLE IF EXISTS public."User_Details";

CREATE TABLE IF NOT EXISTS public."User_Details"
(
    "ID" bigint NOT NULL,
    "FullName" text COLLATE pg_catalog."default" NOT NULL,
    "Email" text COLLATE pg_catalog."default" NOT NULL,
    "Organization" text COLLATE pg_catalog."default",
    "City" text COLLATE pg_catalog."default" NOT NULL,
    "Country" text COLLATE pg_catalog."default" NOT NULL,
    "PurposeOfUse" text COLLATE pg_catalog."default" NOT NULL,
    "Approved" boolean NOT NULL DEFAULT false,
    "Password" text COLLATE pg_catalog."default",
    CONSTRAINT "User_Details_pkey" PRIMARY KEY ("ID")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."User_Details"
    OWNER to mscds;