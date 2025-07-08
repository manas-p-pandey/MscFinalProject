using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.Threading.Tasks;
using DT_App.Models;
using DT_App.ServiceClient;

namespace DT_App.Controllers
{
    public class ForecastController : Controller
    {
        private readonly SiteClient _siteClient;

        public ForecastController(SiteClient siteClient)
        {
            _siteClient = siteClient;
        }

        public async Task<IActionResult> Index()
        {
            var result = await SetupViewModel();
            return View();
        }

        public async Task<IActionResult> TrafficPartial()
        {
            //var result = await SetupViewModel();
            return PartialView("_TrafficPartial");
        }

        public async Task<IActionResult> WeatherPartial()
        {
            //var result = await SetupViewModel();
            return PartialView("_WeatherPartial");
        }

        public async Task<IActionResult> PollutionPartial()
        {
            //var result = await SetupViewModel();
            return PartialView("_PollutionPartial");
        }

        public async Task<IActionResult> CombinedPartial()
        {
            //var result = await SetupViewModel();
            return PartialView("_CombinedPartial");
        }

        private async Task<bool> SetupViewModel()
        {
            try
            {
                ViewBag.SiteList = await _siteClient.GetSitesAsync();
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
