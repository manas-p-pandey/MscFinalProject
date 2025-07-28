using Newtonsoft.Json;

public class TrafficData
{
    [JsonProperty("latitude")]
    public double Latitude { get; set; }

    [JsonProperty("longitude")]
    public double Longitude { get; set; }

    [JsonProperty("traffic_density")]
    public string TrafficDensity { get; set; }
}
