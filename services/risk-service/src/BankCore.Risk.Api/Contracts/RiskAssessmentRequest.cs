using System.Text.Json.Serialization;
using BankCore.Risk.Application.AssessRisk;

namespace BankCore.Risk.Api.Contracts;

public enum RiskOperationType
{
    PIX,
}

public sealed class RiskAssessmentRequest
{
    public const long MaxAmountCents = 99_999_999_999_999;

    [JsonPropertyName("transaction_id")]
    public Guid TransactionId { get; init; }

    [JsonPropertyName("source_account_id")]
    public Guid SourceAccountId { get; init; }

    [JsonPropertyName("destination_account_id")]
    public Guid DestinationAccountId { get; init; }

    [JsonPropertyName("amount_cents")]
    public long AmountCents { get; init; }

    [JsonPropertyName("operation_type")]
    [JsonConverter(typeof(JsonStringEnumConverter))]
    public RiskOperationType OperationType { get; init; }

    public PersistentRiskAssessmentCommand ToCommand()
    {
        if (TransactionId == Guid.Empty)
        {
            throw new ArgumentException("transaction_id is required.", nameof(TransactionId));
        }

        if (SourceAccountId == Guid.Empty)
        {
            throw new ArgumentException("source_account_id is required.", nameof(SourceAccountId));
        }

        if (DestinationAccountId == Guid.Empty)
        {
            throw new ArgumentException("destination_account_id is required.", nameof(DestinationAccountId));
        }

        if (AmountCents <= 0 || AmountCents > MaxAmountCents)
        {
            throw new ArgumentOutOfRangeException(nameof(AmountCents), "amount_cents is outside the allowed range.");
        }

        if (!Enum.IsDefined(OperationType))
        {
            throw new ArgumentException("operation_type is not supported.", nameof(OperationType));
        }

        return new PersistentRiskAssessmentCommand(
            TransactionId,
            SourceAccountId,
            DestinationAccountId,
            AmountCents,
            OperationType.ToString());
    }
}
