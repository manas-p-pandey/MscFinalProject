namespace DT_App.Models
{
    public class SiteModel
    {
        public string site_code { get; set; }
        public string site_name { get; set; }
        public string site_type { get; set; }
        public string local_authority_name { get; set; }
        public double? latitude { get; set; }
        public double? longitude { get; set; }
        public double? latitudewgs84 { get; set; }
        public double? longitudewgs84 { get; set; }
        public DateTime? date_opened { get; set; }
        public DateTime? date_closed { get; set; }
        public string site_link { get; set; }
    }
}
