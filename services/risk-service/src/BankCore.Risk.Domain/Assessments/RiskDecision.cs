namespace BankCore.Risk.Domain.Assessments;

public enum RiskDecision
{
    Approved,
    Review,
    Rejected,
}

public static class RiskDecisionRules
{
    public static RiskDecision FromScore(int score)
    {
        return score switch
        {
            < 0 or > 100 => throw new ArgumentOutOfRangeException(nameof(score), "Risk score must be between 0 and 100."),
            < 40 => RiskDecision.Approved,
            < 70 => RiskDecision.Review,
            _ => RiskDecision.Rejected,
        };
    }
}
