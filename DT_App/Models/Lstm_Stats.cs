namespace DT_App.Models
{
    public class Lstm_Stats
    {
        public DateTime Created_at {  get; set; }
        public string Model_Name { get; set; }
        public float Test_Accuracy { get; set; }
        public float Test_Loss { get; set; }
    }
}
