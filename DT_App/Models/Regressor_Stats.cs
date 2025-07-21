namespace DT_App.Models
{
    public class Regressor_Stats
    {
        public DateTime Created_At { get; set; }
        public string Model { get; set; }
        public float Rmse { get; set; }
        public float Mae { get; set; }
        public float R2 { get; set; }
    }
}
