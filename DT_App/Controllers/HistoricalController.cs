using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using DT_App.Models;

namespace DT_App.Controllers
{
    public class HistoricalController : Controller
    {
        private readonly ILogger<HistoricalController> _logger;

        public HistoricalController(ILogger<HistoricalController> logger)
        {
            _logger = logger;
        }

        public IActionResult Index()
        {
            return View();
        }

        public IActionResult TrafficPartial()
        {
            return PartialView("_TrafficPartial");
        }

        public IActionResult WeatherPartial()
        {
            return PartialView("_WeatherPartial");
        }

        public IActionResult PollutionPartial()
        {
            return PartialView("_PollutionPartial");
        }

        public IActionResult CombinedPartial()
        {
            return PartialView("_CombinedPartial");
        }
    }
}
