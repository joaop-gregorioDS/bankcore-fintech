using BankCore.Risk.Domain.Rules;

namespace BankCore.Risk.Application.AssessRisk;

public sealed record AssessRiskCommand
{
    public AssessRiskCommand(
        Guid transactionId,
        long amountCents,
        string operationType,
        string rulesVersion = RiskRuleSet.CurrentVersion)
    {
        if (transactionId == Guid.Empty)
        {
            throw new ArgumentException("Transaction ID is required.", nameof(transactionId));
        }

        if (amountCents <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amountCents), "Amount in cents must be positive.");
        }

        if (string.IsNullOrWhiteSpace(operationType))
        {
            throw new ArgumentException("Operation type is required.", nameof(operationType));
        }

        if (string.IsNullOrWhiteSpace(rulesVersion))
        {
            throw new ArgumentException("Rules version is required.", nameof(rulesVersion));
        }

        TransactionId = transactionId;
        AmountCents = amountCents;
        OperationType = operationType.Trim().ToUpperInvariant();
        RulesVersion = rulesVersion.Trim();
    }

    public Guid TransactionId { get; }

    public long AmountCents { get; }

    public string OperationType { get; }

    public string RulesVersion { get; }
}
