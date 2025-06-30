-- AQI data quesries

SELECT 
    aqi.id,
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
FROM 
    public.aqi_table AS aqi
JOIN 
    public.aqi_site_table AS site
ON 
    aqi.site_code = site.site_code
ORDER BY 
    aqi.measurement_datetime DESC;
