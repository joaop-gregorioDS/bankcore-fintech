using BankCore.Risk.Domain.Assessments;

namespace BankCore.Risk.Domain.Rules;

public sealed record RiskRuleResult
{
    public RiskRuleResult(int points, IReadOnlyList<RiskReason> reasons)
    {
        if (points < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(points), "Rule points cannot be negative.");
        }

        if (reasons is null)
        {
            throw new ArgumentNullException(nameof(reasons));
        }

        Points = points;
        Reasons = reasons;
    }

    public int Points { get; }

    public IReadOnlyList<RiskReason> Reasons { get; }

    public static RiskRuleResult None => new(0, Array.Empty<RiskReason>());
}
