using BankCore.Risk.Domain.Assessments;

namespace BankCore.Risk.Domain.Rules;

public sealed class OperationTypeRule : IRiskRule
{
    public const string SupportedOperationType = "PIX";

    public string Name => nameof(OperationTypeRule);

    public RiskRuleResult Evaluate(RiskRuleContext context)
    {
        if (context.OperationType == SupportedOperationType)
        {
            return RiskRuleResult.None;
        }

        return new RiskRuleResult(40, new[] { new RiskReason("UNSUPPORTED_OPERATION", 40) });
    }
}
