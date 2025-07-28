using Microsoft.AspNetCore.Mvc;
using DT_App.ServiceClient;

namespace DT_App.Controllers
{
    public class AnalyticsController : Controller
    {
        private readonly SiteClient _siteClient;
        private readonly DataClient _dataClient;

        public AnalyticsController(SiteClient siteClient, DataClient dataClient)
        {
            _siteClient = siteClient;
            _dataClient = dataClient;
        }

        // default call
        public async Task<IActionResult> Index(DateTime queryDatetime)
        {
            var result = await SetupViewModel(queryDatetime);
            return View();
        }

        public async Task<IActionResult> GetHistoricalDataByDate(DateTime queryDatetime)
        {
            var hdResponse = await _dataClient.GetHistoricalDataAsync(queryDatetime.ToString("yyyy-MM-dd HH:00:00"));
            if (hdResponse.StatusCode != "201")
            {
                return BadRequest(new { message = hdResponse.StatusMessage });
            }
            return Ok(hdResponse);
        }

        private async Task<bool> SetupViewModel(DateTime queryDateTime)
        {
            try
            {
                ViewBag.SiteList = await _siteClient.GetSitesAsync();
                var hdResponse = await _dataClient.GetHistoricalDataAsync(queryDateTime.ToString("yyyy-MM-dd HH:00:00"));
                ViewBag.DataList = hdResponse.Data;
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
