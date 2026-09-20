using BankCore.Risk.Domain.Rules;

namespace BankCore.Risk.Application.AssessRisk;

public sealed record PersistentRiskAssessmentCommand
{
    public PersistentRiskAssessmentCommand(
        Guid transactionId,
        Guid sourceAccountId,
        Guid destinationAccountId,
        long amountCents,
        string operationType,
        string rulesVersion = RiskRuleSet.CurrentVersion)
    {
        if (transactionId == Guid.Empty)
        {
            throw new ArgumentException("Transaction ID is required.", nameof(transactionId));
        }

        if (sourceAccountId == Guid.Empty)
        {
            throw new ArgumentException("Source account ID is required.", nameof(sourceAccountId));
        }

        if (destinationAccountId == Guid.Empty)
        {
            throw new ArgumentException("Destination account ID is required.", nameof(destinationAccountId));
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
        SourceAccountId = sourceAccountId;
        DestinationAccountId = destinationAccountId;
        AmountCents = amountCents;
        OperationType = operationType.Trim().ToUpperInvariant();
        RulesVersion = rulesVersion.Trim();
    }

    public Guid TransactionId { get; }

    public Guid SourceAccountId { get; }

    public Guid DestinationAccountId { get; }

    public long AmountCents { get; }

    public string OperationType { get; }

    public string RulesVersion { get; }

    public AssessRiskCommand ToDomainCommand() =>
        new(TransactionId, AmountCents, OperationType, RulesVersion);
}
