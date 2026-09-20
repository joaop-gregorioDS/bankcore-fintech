namespace BankCore.Risk.Application.AssessRisk;

public interface IPersistentRiskAssessmentService
{
    Task<PersistedRiskAssessment> AssessAsync(
        PersistentRiskAssessmentCommand command,
        CancellationToken cancellationToken = default);
}
