using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace BankCore.Risk.Application.AssessRisk;

public static class RiskRequestFingerprint
{
    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.Default,
        WriteIndented = false,
    };

    public static string Compute(PersistentRiskAssessmentCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);

        var normalized = new NormalizedRiskRequest(
            command.AmountCents,
            command.DestinationAccountId,
            command.OperationType,
            command.SourceAccountId,
            command.TransactionId);
        var canonicalJson = JsonSerializer.Serialize(normalized, SerializerOptions);
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonicalJson))).ToLowerInvariant();
    }

    private sealed record NormalizedRiskRequest(
        [property: JsonPropertyName("amount_cents")] long AmountCents,
        [property: JsonPropertyName("destination_account_id")] Guid DestinationAccountId,
        [property: JsonPropertyName("operation_type")] string OperationType,
        [property: JsonPropertyName("source_account_id")] Guid SourceAccountId,
        [property: JsonPropertyName("transaction_id")] Guid TransactionId);
}
