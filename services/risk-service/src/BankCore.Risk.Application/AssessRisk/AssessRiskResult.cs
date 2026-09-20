using BankCore.Risk.Domain.Assessments;

namespace BankCore.Risk.Application.AssessRisk;

public sealed record AssessRiskResult(RiskAssessment Assessment)
{
    public RiskDecision Decision => Assessment.Decision;

    public int RiskScore => Assessment.RiskScore;

    public IReadOnlyList<RiskReason> Reasons => Assessment.Reasons;

    public string RulesVersion => Assessment.RulesVersion;
}
