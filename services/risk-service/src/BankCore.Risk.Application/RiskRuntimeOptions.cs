namespace BankCore.Risk.Application;

public sealed class RiskRuntimeOptions
{
    public const string SectionName = "Risk";

    public string ServiceName { get; init; } = "bankcore-risk";

    public string EnvironmentName { get; init; } = "Production";
}
