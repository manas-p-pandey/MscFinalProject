using Microsoft.AspNetCore.Mvc;
using DT_App.ServiceClient;
using DT_App.Models;

namespace DT_App.Controllers
{
    public class ForecastController : Controller
    {
        private readonly SiteClient _siteClient;
        private readonly DataClient _dataClient;

        public ForecastController(SiteClient siteClient, DataClient dataClient)
        {
            _siteClient = siteClient;
            _dataClient = dataClient;
        }

        public async Task<IActionResult> Index(DateTime queryDatetime, ForecastRequest request)
        {
            if(queryDatetime== DateTime.MinValue)
            {
                queryDatetime = new DateTime(DateTime.Now.Year, DateTime.Now.Month, DateTime.Now.Day, DateTime.Now.Hour, 0, 0);

            }
            var result = await SetupViewModel(queryDatetime, request);
            return View();
        }

        [HttpPost]
        public async Task<IActionResult> GetForecastDataByDate([FromBody] ForecastRequest request)
        {
            Console.WriteLine("Received datetime: " + request?.DateTime);
            Console.WriteLine("Traffic count: " + request?.TrafficData?.Count);

            var forecastResponse = await _dataClient.GetForecastDataAsync(request);

            if (forecastResponse.StatusCode != "201")
            {
                return BadRequest(new { message = forecastResponse.StatusMessage });
            }
            return Ok(forecastResponse);
        }

        private async Task<bool> SetupViewModel(DateTime queryDatetime, ForecastRequest request)
        {
            try
            {
                var siteData = await _siteClient.GetSitesAsync();
                ViewBag.SiteList = siteData;
                if (request.TrafficData==null || !request.TrafficData.Any())
                {
                    var traffic = new List<TrafficData>();
                    foreach (var site in siteData)
                    {
                        var trafficData = new TrafficData
                        {
                            Latitude = site.latitude??0,
                            Longitude = site.longitude??0,
                            TrafficDensity = "moderate_low" // Default value, can be adjusted
                        };
                        traffic.Add(trafficData);
                    }
                    request = new ForecastRequest
                    {
                        DateTime = queryDatetime,
                        TrafficData = traffic
                    };
                }
                var fResponse = await _dataClient.GetForecastDataAsync(request);
                ViewBag.DataList = fResponse.Data;
                ViewBag.LastQueryDate = queryDatetime;
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
