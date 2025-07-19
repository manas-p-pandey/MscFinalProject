namespace DT_App.Models;

public class APIResponseModel
{
    public string StatusCode { get; set; }
    public string StatusMessage { get; set; }
    public int RecordCount { get; set; }
    public List<DataView> Data { get; set; }
}
