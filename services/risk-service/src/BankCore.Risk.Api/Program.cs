using BankCore.Risk.Application;
using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Api.Contracts;
using BankCore.Risk.Infrastructure.Authentication;
using Microsoft.Extensions.Options;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole();

builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow;
});

builder.Services
    .AddOptions<RiskRuntimeOptions>()
    .Bind(builder.Configuration.GetSection(RiskRuntimeOptions.SectionName))
    .Validate(options => !string.IsNullOrWhiteSpace(options.ServiceName), "Risk service name is required.")
    .ValidateOnStart();

builder.Services.AddSingleton<AssessRiskHandler>(_ => new AssessRiskHandler());
builder.Services.AddRiskAuthentication(builder.Configuration);

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

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

app.MapPost("/internal/risk/assessments", (RiskAssessmentRequest request, AssessRiskHandler handler) =>
{
    try
    {
        var result = handler.Handle(request.ToCommand());
        return Results.Ok(RiskAssessmentResponse.From(result));
    }
    catch (ArgumentException)
    {
        return Results.BadRequest(new ApiErrorResponse("invalid_request", "Request de avaliação inválido."));
    }
}).RequireAuthorization(RiskAuthenticationExtensions.AssessmentPolicy);

app.Run();

public partial class Program;
