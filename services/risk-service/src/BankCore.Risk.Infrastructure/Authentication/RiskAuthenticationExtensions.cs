using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.IdentityModel.Tokens;

namespace BankCore.Risk.Infrastructure.Authentication;

public static partial class RiskAuthenticationExtensions
{
    public const string AssessmentPolicy = "RiskAssessment";
    public const string RequiredScope = "risk:assess";
    public const string RequiredSubject = "service:transactions";

    public static IServiceCollection AddRiskAuthentication(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var jwtOptions = new RiskJwtOptions();
        configuration.GetSection(RiskJwtOptions.SectionName).Bind(jwtOptions);

        if (string.IsNullOrWhiteSpace(jwtOptions.Issuer)
            || string.IsNullOrWhiteSpace(jwtOptions.Audience)
            || string.IsNullOrWhiteSpace(jwtOptions.PublicKeysDirectory))
        {
            throw new InvalidOperationException("Risk JWT configuration is incomplete.");
        }

        services.AddSingleton(jwtOptions);
        services
            .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.MapInboundClaims = false;
                options.RequireHttpsMetadata = false;
                options.SaveToken = false;
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidateIssuerSigningKey = true,
                    IssuerSigningKeyResolver = (_, _, kid, _) => LoadPublicKey(jwtOptions, kid),
                    ValidateIssuer = true,
                    ValidIssuer = jwtOptions.Issuer,
                    ValidateAudience = true,
                    ValidAudience = jwtOptions.Audience,
                    ValidateLifetime = true,
                    RequireExpirationTime = true,
                    RequireSignedTokens = true,
                    ClockSkew = TimeSpan.Zero,
                    ValidAlgorithms = new[] { SecurityAlgorithms.RsaSha256 },
                };
                options.Events = new JwtBearerEvents
                {
                    OnAuthenticationFailed = context =>
                    {
                        var logger = context.HttpContext.RequestServices
                            .GetRequiredService<ILoggerFactory>()
                            .CreateLogger("BankCore.Risk.Authentication");
                        logger.LogWarning(
                            "{Event} {FailureType} {RequestId} {CorrelationId}",
                            "risk.authentication.failed",
                            context.Exception.GetType().Name,
                            context.HttpContext.Items["BankCore.RequestId"],
                            context.HttpContext.Items["BankCore.CorrelationId"]);
                        return Task.CompletedTask;
                    },
                    OnTokenValidated = context =>
                    {
                        if (!HasRequiredClaims(context.Principal))
                        {
                            context.Fail("Token sem claims internas obrigatórias.");
                        }

                        return Task.CompletedTask;
                    },
                };
            });

        services.AddAuthorization(options =>
        {
            options.AddPolicy(AssessmentPolicy, policy =>
            {
                policy.RequireAuthenticatedUser();
                policy.RequireClaim("scope", RequiredScope);
            });
        });

        return services;
    }

    private static bool HasRequiredClaims(System.Security.Claims.ClaimsPrincipal? principal)
    {
        if (principal is null)
        {
            return false;
        }

        var required = new[] { "sub", "iss", "aud", "iat", "nbf", "exp", "jti" };
        if (required.Any(claim => string.IsNullOrWhiteSpace(principal.FindFirst(claim)?.Value)))
        {
            return false;
        }

        if (!string.Equals(principal.FindFirst("sub")?.Value, RequiredSubject, StringComparison.Ordinal))
        {
            return false;
        }

        if (!long.TryParse(principal.FindFirst("iat")?.Value, out var issuedAt))
        {
            return false;
        }

        return issuedAt <= DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    }

    private static IEnumerable<SecurityKey> LoadPublicKey(RiskJwtOptions options, string? kid)
    {
        if (string.IsNullOrWhiteSpace(kid) || !KidPattern().IsMatch(kid))
        {
            return Array.Empty<SecurityKey>();
        }

        var path = Path.Combine(options.PublicKeysDirectory, $"{kid}.pem");
        try
        {
            var rsa = RSA.Create();
            rsa.ImportFromPem(File.ReadAllText(path));
            return new[] { new RsaSecurityKey(rsa) { KeyId = kid } };
        }
        catch (IOException)
        {
            return Array.Empty<SecurityKey>();
        }
        catch (UnauthorizedAccessException)
        {
            return Array.Empty<SecurityKey>();
        }
        catch (CryptographicException)
        {
            return Array.Empty<SecurityKey>();
        }
        catch (ArgumentException)
        {
            return Array.Empty<SecurityKey>();
        }
    }

    [GeneratedRegex("^[A-Za-z0-9._-]+$", RegexOptions.CultureInvariant)]
    private static partial Regex KidPattern();
}
