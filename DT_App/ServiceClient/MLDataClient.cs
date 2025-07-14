using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using DT_App.Models;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;

namespace DT_App.ServiceClient
{
    public class MLDataClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public MLDataClient(HttpClient httpClient, IOptions<ApiSettings> apiSettings)
        {
            _httpClient = httpClient;
            _baseUrl = apiSettings.Value.BaseUrl;
        }

        public async Task<List<MLDataView>> GetHistoricalDataAsync(string queryDatetime)
        {
            var response = await _httpClient.GetAsync($"{_baseUrl}/historical_data/?datetime_value={queryDatetime}");
            if(!response.IsSuccessStatusCode)
                return new List<MLDataView>();
            response.EnsureSuccessStatusCode();
            var jsonString = await response.Content.ReadAsStringAsync();
            var mlDataList = JsonConvert.DeserializeObject<List<MLDataView>>(jsonString);
            return mlDataList??new List<MLDataView>();
        }
    }
}
