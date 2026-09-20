using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.IdentityModel.Tokens;
using Microsoft.Extensions.Configuration;
using Xunit;

namespace BankCore.Risk.UnitTests;

public sealed class RiskApiContractTests : IClassFixture<RiskApiFactory>
{
    private readonly RiskApiFactory _factory;

    public RiskApiContractTests(RiskApiFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task Valid_internal_token_returns_assessment_contract()
    {
        using var client = _factory.CreateClient();
        var token = _factory.CreateToken();
        var parsedToken = new JwtSecurityTokenHandler().ReadJwtToken(token);
        Assert.Equal("risk-test-key", parsedToken.Header.Kid);
        Assert.True(File.Exists(Path.Combine(_factory.PublicKeysDirectory, "risk-test-key.pem")));
        using var request = CreateRequest(token);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.NotEqual(Guid.Empty, document.RootElement.GetProperty("assessment_id").GetGuid());
        Assert.Equal("REVIEW", document.RootElement.GetProperty("decision").GetString());
        Assert.Equal(40, document.RootElement.GetProperty("risk_score").GetInt32());
        Assert.Equal("HIGH_AMOUNT", document.RootElement.GetProperty("reasons")[0].GetString());
        Assert.Equal("risk-rules-v1", document.RootElement.GetProperty("rules_version").GetString());
    }

    [Fact]
    public async Task Missing_token_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest();

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task User_token_with_public_audience_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(audience: "bankcore-api", subject: "user:123"));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Wrong_scope_returns_403()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(scope: "service:transactions"));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task Wrong_audience_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(audience: "wrong-audience"));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Wrong_issuer_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(issuer: "other-issuer"));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Expired_token_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(expiresUtc: DateTime.UtcNow.AddMinutes(-1)));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Unknown_kid_returns_401()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(kid: "unknown-key"));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Invalid_signature_returns_401()
    {
        using var unrelatedKey = RSA.Create(2048);
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(signingKey: unrelatedKey));

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Zero_amount_returns_400()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(), amountCents: 0);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Negative_amount_returns_400()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(), amountCents: -1);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Invalid_uuid_returns_400()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(), transactionId: "not-a-uuid");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Unsupported_operation_returns_400()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(), operationType: "CARD");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Unknown_properties_are_rejected()
    {
        using var client = _factory.CreateClient();
        using var request = CreateRequest(_factory.CreateToken(), extraProperty: true);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Repeated_request_keeps_domain_result_deterministic_but_ids_are_not_durable_yet()
    {
        using var client = _factory.CreateClient();
        var token = _factory.CreateToken();
        using var firstRequest = CreateRequest(token);
        using var secondRequest = CreateRequest(token);

        using var firstResponse = await client.SendAsync(firstRequest);
        using var secondResponse = await client.SendAsync(secondRequest);
        using var first = JsonDocument.Parse(await firstResponse.Content.ReadAsStringAsync());
        using var second = JsonDocument.Parse(await secondResponse.Content.ReadAsStringAsync());

        Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondResponse.StatusCode);
        Assert.NotEqual(
            first.RootElement.GetProperty("assessment_id").GetGuid(),
            second.RootElement.GetProperty("assessment_id").GetGuid());
        Assert.Equal(
            first.RootElement.GetProperty("decision").GetString(),
            second.RootElement.GetProperty("decision").GetString());
        Assert.Equal(
            first.RootElement.GetProperty("risk_score").GetInt32(),
            second.RootElement.GetProperty("risk_score").GetInt32());
        Assert.Equal(
            first.RootElement.GetProperty("reasons").GetRawText(),
            second.RootElement.GetProperty("reasons").GetRawText());
    }

    private static HttpRequestMessage CreateRequest(
        string? token = null,
        long amountCents = 250_000,
        string transactionId = "11111111-1111-1111-1111-111111111111",
        string operationType = "PIX",
        bool extraProperty = false)
    {
        var extra = extraProperty ? ",\"unexpected\":true" : string.Empty;
        var request = new HttpRequestMessage(HttpMethod.Post, "/internal/risk/assessments")
        {
            Content = new StringContent(
                $$"""{"transaction_id":"{{transactionId}}","source_account_id":"22222222-2222-2222-2222-222222222222","destination_account_id":"33333333-3333-3333-3333-333333333333","amount_cents":{{amountCents}},"operation_type":"{{operationType}}"{{extra}}}""",
                Encoding.UTF8,
                "application/json"),
        };

        if (token is not null)
        {
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token);
        }

        return request;
    }
}

public sealed class RiskApiFactory : WebApplicationFactory<Program>
{
    private const string KeyId = "risk-test-key";
    private const string Issuer = "bankcore-auth";
    private const string Audience = "bankcore-internal";
    private readonly RSA _signingKey = RSA.Create(2048);
    private readonly string _publicKeysDirectory = Path.Combine(Path.GetTempPath(), $"bankcore-risk-{Guid.NewGuid():N}");

    public RiskApiFactory()
    {
        Directory.CreateDirectory(_publicKeysDirectory);
        File.WriteAllText(
            Path.Combine(_publicKeysDirectory, $"{KeyId}.pem"),
            _signingKey.ExportSubjectPublicKeyInfoPem());
    }

    public string PublicKeysDirectory => _publicKeysDirectory;

    public string CreateToken(
        string audience = Audience,
        string scope = "risk:assess",
        string kid = KeyId,
        DateTime? expiresUtc = null,
        RSA? signingKey = null,
        string subject = "service:transactions",
        string issuer = Issuer)
    {
        var now = DateTime.UtcNow;
        var expires = expiresUtc ?? now.AddMinutes(5);
        var notBefore = expires <= now ? expires.AddMinutes(-2) : now.AddMinutes(-1);
        var nowSeconds = new DateTimeOffset(notBefore).ToUnixTimeSeconds();
        var signingCredentials = new SigningCredentials(
            new RsaSecurityKey(signingKey ?? _signingKey) { KeyId = kid },
            SecurityAlgorithms.RsaSha256);
        var token = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: new[]
            {
                new Claim(JwtRegisteredClaimNames.Sub, subject),
                new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
                new Claim(JwtRegisteredClaimNames.Iat, nowSeconds.ToString(), ClaimValueTypes.Integer64),
                new Claim(JwtRegisteredClaimNames.Nbf, nowSeconds.ToString(), ClaimValueTypes.Integer64),
                new Claim("scope", scope),
            },
            notBefore: notBefore,
            expires: expires,
            signingCredentials: signingCredentials);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("RiskJwt:Issuer", Issuer);
        builder.UseSetting("RiskJwt:Audience", Audience);
        builder.UseSetting("RiskJwt:PublicKeysDirectory", _publicKeysDirectory);
        builder.ConfigureAppConfiguration((_, configuration) =>
        {
            configuration.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["RiskJwt:Issuer"] = Issuer,
                ["RiskJwt:Audience"] = Audience,
                ["RiskJwt:PublicKeysDirectory"] = _publicKeysDirectory,
            });
        });
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (disposing)
        {
            _signingKey.Dispose();
            if (Directory.Exists(_publicKeysDirectory))
            {
                Directory.Delete(_publicKeysDirectory, recursive: true);
            }
        }
    }
}
