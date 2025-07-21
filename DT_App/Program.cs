using DT_App.ServiceClient;
using DT_App;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Bind ApiSettings
builder.Services.Configure<ApiSettings>(builder.Configuration.GetSection("ApiSettings"));

// Register HttpClient and SiteClient
builder.Services.AddHttpClient<SiteClient>();
// Register HttpClient and DataClient
builder.Services.AddHttpClient<DataClient>();
// Register Dashboard Client
builder.Services.AddHttpClient<DashboardClient>();


// controllers
builder.Services.AddControllersWithViews();
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8080); // Important: not localhost
});
var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseRouting();

app.UseAuthorization();

app.MapStaticAssets();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}")
    .WithStaticAssets();


app.Run();
