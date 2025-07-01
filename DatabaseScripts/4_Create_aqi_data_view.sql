-- View: public.aqi_data_view

-- DROP VIEW public.aqi_data_view;

CREATE OR REPLACE VIEW public.aqi_data_view
 AS
 SELECT DISTINCT aqi.id,
    aqi.site_code,
    site.site_name,
    site.site_type,
    site.local_authority_name,
    site.latitude,
    site.longitude,
    site.date_opened,
    site.date_closed,
    site.site_link,
    aqi.measurement_datetime,
    aqi.nitric_oxide,
    aqi.nitrogen_dioxide,
    aqi.oxides_of_nitrogen,
    aqi.pm10,
    aqi.pm25
   FROM aqi_table aqi
     JOIN aqi_site_table site ON aqi.site_code = site.site_code
  ORDER BY aqi.measurement_datetime DESC;

ALTER TABLE public.aqi_data_view
    OWNER TO postgres;

