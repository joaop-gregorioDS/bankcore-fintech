using BankCore.Risk.Domain.Assessments;

namespace BankCore.Risk.Domain.Rules;

public sealed class AmountRiskRule : IRiskRule
{
    public const long StandardLimitCents = 100_000;

    public const long CriticalLimitCents = 1_000_000;

    public string Name => nameof(AmountRiskRule);

    public RiskRuleResult Evaluate(RiskRuleContext context)
    {
        if (context.AmountCents > CriticalLimitCents)
        {
            return new RiskRuleResult(70, new[] { new RiskReason("VERY_HIGH_AMOUNT", 70) });
        }

        if (context.AmountCents > StandardLimitCents)
        {
            return new RiskRuleResult(40, new[] { new RiskReason("HIGH_AMOUNT", 40) });
        }

        return RiskRuleResult.None;
    }
}
