using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using DT_App.Models;
using DT_App.ServiceClient;
using Newtonsoft.Json;

namespace DT_App.Controllers;

public class HomeController : Controller
{
    private readonly DashboardClient _dashboardClient;

    public HomeController(DashboardClient dashboardClient)
    {
        _dashboardClient = dashboardClient;
    }

    public async Task<IActionResult> Index()
    {
        var dashboardData = await _dashboardClient.GetDashboardDataAsync();
        var dashboardJson = JsonConvert.SerializeObject(dashboardData);
        ViewBag.DashboardDataJson = dashboardJson;
        return View();
    }
}
