﻿using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using DT_App.Models;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;

namespace DT_App.ServiceClient
{
    public class DataClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public DataClient(HttpClient httpClient, IOptions<ApiSettings> apiSettings)
        {
            _httpClient = httpClient;
            _baseUrl = apiSettings.Value.BaseUrl;
        }

        public async Task<APIResponseModel> GetHistoricalDataAsync(string queryDatetime)
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/historical_data/?datetime_value={queryDatetime}");
                if (!response.IsSuccessStatusCode)
                    return new APIResponseModel
                    {
                        StatusCode= response.StatusCode.ToString(),
                        StatusMessage = "Error returned from API.",
                        RecordCount =0,
                        Data= new List<DataView>()
                    };
                response.EnsureSuccessStatusCode();
                var jsonString = await response.Content.ReadAsStringAsync();
                var historicalData = JsonConvert.DeserializeObject<List<DataView>>(jsonString);
                if(historicalData == null || historicalData.Count()==0)
                    return new APIResponseModel
                    {
                        StatusCode = "404",
                        StatusMessage = "No Data Found",
                        RecordCount = 0,
                        Data = new List<DataView>()
                    };
                else
                {
                    return new APIResponseModel
                    {
                        StatusCode = "201",
                        StatusMessage = "Data Found",
                        RecordCount = historicalData.Count,
                        Data = historicalData
                    };
                }
                
            }
            catch (Exception ex)
            {
                return new APIResponseModel
                {
                    StatusCode = "501",
                    StatusMessage = ex.Message,
                    RecordCount = 0,
                    Data = new List<DataView>()
                };
            }
        }

        public async Task<APIResponseModel> GetForecastDataAsync(string queryDatetime)
        {
            try
            {
                var response = await _httpClient.GetAsync($"{_baseUrl}/forecast_data/?datetime_value={queryDatetime}");
                if (!response.IsSuccessStatusCode)
                    return new APIResponseModel
                    {
                        StatusCode = response.StatusCode.ToString(),
                        StatusMessage = "Error returned from API.",
                        RecordCount = 0,
                        Data = new List<DataView>()
                    };
                response.EnsureSuccessStatusCode();
                var jsonString = await response.Content.ReadAsStringAsync();
                var historicalData = JsonConvert.DeserializeObject<List<DataView>>(jsonString);
                if (historicalData == null || historicalData.Count() == 0)
                    return new APIResponseModel
                    {
                        StatusCode = "404",
                        StatusMessage = "No Data Found",
                        RecordCount = 0,
                        Data = new List<DataView>()
                    };
                else
                {
                    return new APIResponseModel
                    {
                        StatusCode = "404",
                        StatusMessage = "No Data Found",
                        RecordCount = 0,
                        Data = historicalData
                    };
                }

            }
            catch (Exception ex)
            {
                return new APIResponseModel
                {
                    StatusCode = "501",
                    StatusMessage = ex.Message,
                    RecordCount = 0,
                    Data = new List<DataView>()
                };
            }
        }
    }
}
