using System.Text.Json.Serialization;
using BankCore.Risk.Application.AssessRisk;

namespace BankCore.Risk.Api.Contracts;

public sealed class RiskAssessmentResponse
{
    [JsonPropertyName("assessment_id")]
    public Guid AssessmentId { get; init; }

    [JsonPropertyName("transaction_id")]
    public Guid TransactionId { get; init; }

    [JsonPropertyName("decision")]
    public string Decision { get; init; } = string.Empty;

    [JsonPropertyName("risk_score")]
    public int RiskScore { get; init; }

    [JsonPropertyName("reasons")]
    public IReadOnlyList<string> Reasons { get; init; } = Array.Empty<string>();

    [JsonPropertyName("rules_version")]
    public string RulesVersion { get; init; } = string.Empty;

    public static RiskAssessmentResponse From(AssessRiskResult result)
    {
        return new RiskAssessmentResponse
        {
            AssessmentId = Guid.NewGuid(),
            TransactionId = result.Assessment.TransactionId,
            Decision = result.Decision.ToString().ToUpperInvariant(),
            RiskScore = result.RiskScore,
            Reasons = result.Reasons.Select(reason => reason.Code).ToArray(),
            RulesVersion = result.RulesVersion,
        };
    }
}
