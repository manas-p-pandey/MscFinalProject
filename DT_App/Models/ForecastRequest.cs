using DT_App.Models;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;

public class ForecastRequest
{
    [JsonProperty("datetime")]
    public DateTime DateTime { get; set; }

    [JsonProperty("traffic_data")]
    public List<TrafficData> TrafficData { get; set; }
}
