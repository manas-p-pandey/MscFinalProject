using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using DT_App.Models;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;

namespace DT_App.ServiceClient
{
    public class DashboardClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public DashboardClient(HttpClient httpClient, IOptions<ApiSettings> apiSettings)
        {
            _httpClient = httpClient;
            _baseUrl = apiSettings.Value.BaseUrl;
        }

        public async Task<DashboardResponse> GetDashboardDataAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/dashboard/");
                if (!response.IsSuccessStatusCode)
                    return new DashboardResponse
                    {
                        Lstm_Stats= new List<Lstm_Stats>(),

                    };
                response.EnsureSuccessStatusCode();
                var jsonString = await response.Content.ReadAsStringAsync();
                var historicalData = JsonConvert.DeserializeObject<DashboardResponse>(jsonString);
                if((historicalData == null || historicalData.Lstm_Stats == null || historicalData.Lstm_Stats.Count()==0)
                    && (historicalData == null || historicalData.Regressor_Stats == null || historicalData.Regressor_Stats.Count() == 0))
                    return new DashboardResponse
                    {
                        Lstm_Stats = new List<Lstm_Stats>(),
                        Regressor_Stats = new List<Regressor_Stats>(),
                    };
                else
                {
                    return historicalData;
                }
                
            }
            catch (Exception ex)
            {
                return new DashboardResponse
                {
                    Lstm_Stats = new List<Lstm_Stats>(),
                    Regressor_Stats = new List<Regressor_Stats>(),
                };
            }
        }
    }
}
