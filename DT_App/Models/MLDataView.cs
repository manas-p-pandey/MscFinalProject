using System;

namespace DT_App.Models
{
    public class MLDataView
    {
        public string site_code { set; get; }
        public string site_name { set; get; }
        public string site_type { set; get; }
        public double latitude { set; get; }
        public double longitude { set; get; }
        public DateTime datetime { set; get; }
        public int aqi { set; get; }
        public double co { set; get; }
        public double no { set; get; }
        public double no2 { set; get; }
        public double o3 { set; get; }
        public double so2 { set; get; }
        public double pm2_5 { set; get; }
        public double pm10 { set; get; }
        public double nh3 { set; get; }
        public double temp { set; get; }
        public double feels_like { set; get; }
        public int pressure { set; get; }
        public int humidity { set; get; }
        public double dew_point { set; get; }
        public double wind_speed { set; get; }
        public int wind_deg { set; get; }
        public string traffic_flow { set; get; }
        public string traffic_density { set; get; }
    }
}
