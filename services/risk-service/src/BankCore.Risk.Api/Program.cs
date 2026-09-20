using BankCore.Risk.Application;
using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Api.Contracts;
using BankCore.Risk.Infrastructure.Authentication;
using BankCore.Risk.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
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
var riskDatabaseConnection = builder.Configuration.GetConnectionString("RiskDatabase");
if (string.IsNullOrWhiteSpace(riskDatabaseConnection))
{
    throw new InvalidOperationException("ConnectionStrings:RiskDatabase is required.");
}
builder.Services.AddDbContextFactory<RiskDbContext>(options =>
    options.UseNpgsql(
        riskDatabaseConnection,
        npgsql => npgsql.MigrationsAssembly(typeof(RiskDbContext).Assembly.FullName)));
builder.Services.AddScoped<IPersistentRiskAssessmentService, EfRiskAssessmentService>();
builder.Services.AddScoped<RiskDatabaseReadiness>();
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

app.MapGet("/readiness", async (
    IOptions<RiskRuntimeOptions> options,
    RiskDatabaseReadiness readiness,
    CancellationToken cancellationToken) =>
{
    if (!await readiness.IsReadyAsync(cancellationToken))
    {
        return Results.Json(
            new { status = "not_ready", service = options.Value.ServiceName },
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }

    return Results.Ok(new
    {
        status = "ready",
        service = options.Value.ServiceName,
        environment = options.Value.EnvironmentName,
    });
});

app.MapPost("/internal/risk/assessments", async (
    RiskAssessmentRequest request,
    IPersistentRiskAssessmentService service,
    CancellationToken cancellationToken) =>
{
    try
    {
        var result = await service.AssessAsync(request.ToCommand(), cancellationToken);
        return Results.Ok(RiskAssessmentResponse.From(result));
    }
    catch (RiskAssessmentConflictException exception)
    {
        return Results.Conflict(new ApiErrorResponse(
            "assessment_conflict",
            $"A different assessment already exists for transaction {exception.TransactionId}."));
    }
    catch (ArgumentException)
    {
        return Results.BadRequest(new ApiErrorResponse("invalid_request", "Request de avaliação inválido."));
    }
}).RequireAuthorization(RiskAuthenticationExtensions.AssessmentPolicy);

app.Run();

public partial class Program;
