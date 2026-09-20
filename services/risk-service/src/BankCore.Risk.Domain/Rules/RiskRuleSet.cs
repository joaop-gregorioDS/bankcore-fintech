namespace BankCore.Risk.Domain.Rules;

public static class RiskRuleSet
{
    public const string CurrentVersion = "risk-rules-v1";

    public static IReadOnlyList<IRiskRule> CreateV1()
    {
        return new IRiskRule[]
        {
            new AmountRiskRule(),
            new OperationTypeRule(),
        };
    }
}
