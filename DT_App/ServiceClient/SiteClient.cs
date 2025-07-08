using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using DT_App.Models;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;

namespace DT_App.ServiceClient
{
    public class SiteClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public SiteClient(HttpClient httpClient, IOptions<ApiSettings> apiSettings)
        {
            _httpClient = httpClient;
            _baseUrl = apiSettings.Value.BaseUrl;
        }

        public async Task<List<SiteModel>> GetSitesAsync()
        {
            var response = await _httpClient.GetAsync($"{_baseUrl}/sites");
            response.EnsureSuccessStatusCode();
            var jsonString = await response.Content.ReadAsStringAsync();
            var siteList = JsonConvert.DeserializeObject<List<SiteModel>>(jsonString);

            if (siteList == null)
                return new List<SiteModel>();

            // Group by latitude + longitude
            var grouped = siteList
                .GroupBy(s => new { s.latitude, s.longitude })
                .ToList();

            var filteredList = new List<SiteModel>();

            foreach (var group in grouped)
            {
                if (group.Count() == 1)
                {
                    // Only one, add directly
                    filteredList.Add(group.First());
                }
                else
                {
                    // More than one with same lat/lon
                    var withoutNullClosed = group.Where(s => s.date_closed != null).ToList();

                    if (withoutNullClosed.Any())
                    {
                        // Add all sites that have date_closed not null
                        filteredList.AddRange(withoutNullClosed);
                    }
                    else
                    {
                        // If no closed sites, keep all (fallback)
                        filteredList.AddRange(group);
                    }
                }
            }

            return filteredList;
        }
    }
}
