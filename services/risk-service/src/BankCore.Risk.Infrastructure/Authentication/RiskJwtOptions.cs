namespace BankCore.Risk.Infrastructure.Authentication;

public sealed class RiskJwtOptions
{
    public const string SectionName = "RiskJwt";

    public string Issuer { get; set; } = "bankcore-auth";

    public string Audience { get; set; } = "bankcore-internal";

    public string PublicKeysDirectory { get; set; } = "/run/secrets/jwt-public";
}
