using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.Threading.Tasks;
using DT_App.Models;
using DT_App.ServiceClient;

namespace DT_App.Controllers
{
    public class AnalyticsController : Controller
    {
        private readonly SiteClient _siteClient;
        private readonly MLDataClient _mlDataClient;

        public AnalyticsController(SiteClient siteClient, MLDataClient mlClient)
        {
            _siteClient = siteClient;
            _mlDataClient = mlClient;
        }

        // default call
        public async Task<IActionResult> Index(DateTime queryDatetime, int viewID = 0)
        {
            var result = await SetupViewModel(viewID, queryDatetime);
            return View();
        }

        public async Task<IActionResult> TrafficPartial()
        {
            return PartialView("_TrafficPartial");
        }

        public async Task<IActionResult> WeatherPartial()
        {
            return PartialView("_WeatherPartial");
        }

        public async Task<IActionResult> PollutionPartial()
        {
            return PartialView("_PollutionPartial");
        }

        public async Task<IActionResult> CombinedPartial()
        {
            return PartialView("_CombinedPartial");
        }

        private async Task<bool> SetupViewModel(int viewID, DateTime queryDateTime)
        {
            try
            {
                ViewBag.SiteList = await _siteClient.GetSitesAsync();
                ViewBag.MLDataList = await _mlDataClient.GetHistoricalDataAsync(queryDateTime.ToString("yyyy-MM-dd HH:00:00"));
                ViewBag.ViewID = viewID;
                ViewBag.LastQueryDate = queryDateTime;
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
