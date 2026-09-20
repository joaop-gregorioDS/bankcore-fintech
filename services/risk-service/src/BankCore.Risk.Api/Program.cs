using BankCore.Risk.Application;
using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Api.Contracts;
using BankCore.Risk.Infrastructure.Authentication;
using BankCore.Risk.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using System.Text.Json.Serialization;
using System.Diagnostics;
using System.Text.RegularExpressions;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;
using System.Diagnostics.Metrics;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole(options => options.IncludeScopes = true);

var otlpEndpoint = builder.Configuration["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
    ?? builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"];
var otlpMetricsEndpoint = builder.Configuration["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"]
    ?? builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"];
var riskMeter = new Meter("BankCore.Risk", "1.0.0");
var riskAssessments = riskMeter.CreateCounter<long>("bankcore_risk_assessments", "{assessment}");
var riskAssessmentDuration = riskMeter.CreateHistogram<double>(
    "bankcore_risk_assessment_duration_seconds", "s");
builder.Services
    .AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService(
        serviceName: builder.Configuration["RISK:ServiceName"]
            ?? builder.Configuration["RISK__SERVICE_NAME"]
            ?? "bankcore-risk",
        serviceVersion: "1.0.0"))
    .WithTracing(tracing =>
    {
        tracing
            .AddSource("BankCore.Risk")
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation();
        if (!string.IsNullOrWhiteSpace(otlpEndpoint))
        {
            tracing.AddOtlpExporter(options => options.Endpoint = new Uri(otlpEndpoint));
        }
    })
    .WithMetrics(metrics =>
    {
        metrics
            .AddMeter("BankCore.Risk")
            .AddAspNetCoreInstrumentation()
            .AddRuntimeInstrumentation();
        if (!string.IsNullOrWhiteSpace(otlpMetricsEndpoint))
        {
            metrics.AddOtlpExporter(options => options.Endpoint = new Uri(otlpMetricsEndpoint));
        }
    });

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
var riskActivitySource = new ActivitySource("BankCore.Risk");

app.Use(async (context, next) =>
{
    var requestId = NormalizeContextId(context.Request.Headers["X-Request-ID"].FirstOrDefault());
    var correlationId = NormalizeContextId(context.Request.Headers["X-Correlation-ID"].FirstOrDefault());
    context.Items["BankCore.RequestId"] = requestId;
    context.Items["BankCore.CorrelationId"] = correlationId;
    context.Response.Headers["X-Request-ID"] = requestId;
    context.Response.Headers["X-Correlation-ID"] = correlationId;
    var started = Stopwatch.GetTimestamp();

    try
    {
        await next();
    }
    finally
    {
        app.Logger.LogInformation(
            "{Event} {RequestId} {CorrelationId} {Status} {DurationMs}",
            "http.request.completed",
            requestId,
            correlationId,
            context.Response.StatusCode,
            Math.Round(Stopwatch.GetElapsedTime(started).TotalMilliseconds, 2));
    }
});

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
    HttpContext context,
    CancellationToken cancellationToken) =>
{
    var assessmentStarted = Stopwatch.GetTimestamp();
    try
    {
        using var assessmentActivity = riskActivitySource.StartActivity("risk.assess");
        assessmentActivity?.SetTag("risk.operation_type", request.OperationType);
        var result = await service.AssessAsync(request.ToCommand(), cancellationToken);
        var decision = result.Assessment.Decision.ToString().ToUpperInvariant();
        riskAssessments.Add(1, new KeyValuePair<string, object?>("decision", decision));
        riskAssessmentDuration.Record(
            Stopwatch.GetElapsedTime(assessmentStarted).TotalSeconds,
            new KeyValuePair<string, object?>("decision", decision));
        assessmentActivity?.SetTag("risk.decision", decision);
        assessmentActivity?.SetTag("risk.rules_version", result.Assessment.RulesVersion);
        app.Logger.LogInformation(
            "{Event} {RequestId} {CorrelationId} {TraceId} {SpanId} {TransactionId} {RiskAssessmentId} {Decision} {RulesVersion} {Status}",
            "risk.assessment.completed",
            context.Items["BankCore.RequestId"],
            context.Items["BankCore.CorrelationId"],
            Activity.Current?.TraceId.ToString(),
            Activity.Current?.SpanId.ToString(),
            request.TransactionId,
            result.AssessmentId,
            result.Assessment.Decision.ToString().ToUpperInvariant(),
            result.Assessment.RulesVersion,
            StatusCodes.Status200OK);
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

static string NormalizeContextId(string? value)
{
    return !string.IsNullOrWhiteSpace(value)
        && Regex.IsMatch(value, "^[A-Za-z0-9._:-]{1,128}$", RegexOptions.CultureInvariant)
        ? value
        : Guid.NewGuid().ToString();
}

public partial class Program;
