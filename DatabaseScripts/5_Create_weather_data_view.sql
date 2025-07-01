CREATE OR REPLACE VIEW weather_data_view AS
SELECT
    w.id,
    w.latitude,
    w.longitude,
    -- Convert timestamp with time zone to local datetime without offset
    (w.timestamp AT TIME ZONE 'Europe/London')::timestamp AS local_datetime,
    w.temp,
    w.feels_like,
    w.pressure,
    w.humidity,
    w.dew_point,
    w.uvi,
    w.clouds,
    w.visibility,
    w.wind_speed,
    w.wind_deg,
    w.weather_main,
    w.weather_description,
    s.site_code,
    s.site_name,
    s.site_type,
    s.local_authority_name,
    s.latitudeWGS84,
    s.longitudeWGS84,
    s.date_opened,
    s.date_closed,
    s.site_link
FROM
    weather_table w
JOIN
    aqi_site_table s
ON
    w.latitude = s.latitude
    AND w.longitude = s.longitude;

ALTER TABLE public.weather_data_view
    OWNER TO postgres;
