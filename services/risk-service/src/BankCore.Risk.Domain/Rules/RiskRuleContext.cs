namespace BankCore.Risk.Domain.Rules;

public sealed record RiskRuleContext
{
    public RiskRuleContext(long amountCents, string operationType)
    {
        if (amountCents <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(amountCents), "Amount in cents must be positive.");
        }

        if (string.IsNullOrWhiteSpace(operationType))
        {
            throw new ArgumentException("Operation type is required.", nameof(operationType));
        }

        AmountCents = amountCents;
        OperationType = operationType.Trim().ToUpperInvariant();
    }

    public long AmountCents { get; }

    public string OperationType { get; }
}
