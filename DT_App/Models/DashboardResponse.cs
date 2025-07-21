namespace DT_App.Models
{
    public class DashboardResponse
    {
        public List<Lstm_Stats> Lstm_Stats { get; set; }
        public List<Regressor_Stats> Regressor_Stats { get; set; }
    }
}
