namespace BankCore.Risk.Infrastructure.Persistence;

public sealed class RiskAssessmentEntity
{
    public Guid Id { get; set; }

    public Guid TransactionId { get; set; }

    public Guid SourceAccountId { get; set; }

    public Guid DestinationAccountId { get; set; }

    public long AmountCents { get; set; }

    public string OperationType { get; set; } = string.Empty;

    public string RequestFingerprint { get; set; } = string.Empty;

    public string Decision { get; set; } = string.Empty;

    public int RiskScore { get; set; }

    public string ReasonsJson { get; set; } = "[]";

    public string RulesVersion { get; set; } = string.Empty;

    public DateTimeOffset CreatedAt { get; set; }
}
