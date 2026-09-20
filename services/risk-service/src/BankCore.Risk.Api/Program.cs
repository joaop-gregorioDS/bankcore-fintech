using BankCore.Risk.Application;
using Microsoft.Extensions.Options;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole();

builder.Services
    .AddOptions<RiskRuntimeOptions>()
    .Bind(builder.Configuration.GetSection(RiskRuntimeOptions.SectionName))
    .Validate(options => !string.IsNullOrWhiteSpace(options.ServiceName), "Risk service name is required.")
    .ValidateOnStart();

var app = builder.Build();

app.MapGet("/health", (IOptions<RiskRuntimeOptions> options) =>
    Results.Ok(new
    {
        status = "healthy",
        service = options.Value.ServiceName,
    }));

app.MapGet("/readiness", (IOptions<RiskRuntimeOptions> options) =>
    Results.Ok(new
    {
        status = "ready",
        service = options.Value.ServiceName,
        environment = options.Value.EnvironmentName,
    }));

app.Run();

public partial class Program;
