using BankCore.Risk.Domain.Assessments;

namespace BankCore.Risk.Application.AssessRisk;

public sealed record PersistedRiskAssessment(Guid AssessmentId, RiskAssessment Assessment);
