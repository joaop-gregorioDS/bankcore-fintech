namespace BankCore.Risk.Domain.Assessments;

public sealed record RiskAssessment
{
    public RiskAssessment(
        Guid transactionId,
        RiskDecision decision,
        RiskScore score,
        IReadOnlyList<RiskReason> reasons,
        string rulesVersion)
    {
        if (transactionId == Guid.Empty)
        {
            throw new ArgumentException("Transaction ID is required.", nameof(transactionId));
        }

        if (reasons is null)
        {
            throw new ArgumentNullException(nameof(reasons));
        }

        if (string.IsNullOrWhiteSpace(rulesVersion))
        {
            throw new ArgumentException("Rules version is required.", nameof(rulesVersion));
        }

        if (RiskDecisionRules.FromScore(score.Value) != decision)
        {
            throw new ArgumentException("Decision does not match the risk score.", nameof(decision));
        }

        TransactionId = transactionId;
        Decision = decision;
        Score = score;
        Reasons = reasons;
        RulesVersion = rulesVersion;
    }

    public Guid TransactionId { get; }

    public RiskDecision Decision { get; }

    public RiskScore Score { get; }

    public int RiskScore => Score.Value;

    public IReadOnlyList<RiskReason> Reasons { get; }

    public string RulesVersion { get; }
}
