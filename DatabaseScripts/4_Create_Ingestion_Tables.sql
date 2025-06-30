CREATE TABLE traffic_table (
    id SERIAL PRIMARY KEY,
    location TEXT,
    speed INTEGER,
    timestamp TIMESTAMP
);

CREATE TABLE aqi_data (
    id SERIAL PRIMARY KEY,
    local_authority_name TEXT,
    local_authority_code TEXT,
    site_code TEXT NOT NULL,
    site_name TEXT,
    site_type TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    bulletin_datetime TIMESTAMP NOT NULL,
    species_code TEXT NOT NULL,
    species_description TEXT,
    air_quality_index INTEGER,
    air_quality_band TEXT,
    index_source TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (site_code, bulletin_datetime, species_code) 
);

CREATE TABLE weather_table (
    id SERIAL PRIMARY KEY,
    location TEXT,
    wind_speed INTEGER,
    temp INTEGER,
    timestamp TIMESTAMP
);
