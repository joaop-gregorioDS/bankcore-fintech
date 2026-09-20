using System.Text.Json;
using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Domain.Assessments;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace BankCore.Risk.Infrastructure.Persistence;

public sealed class EfRiskAssessmentService(
    IDbContextFactory<RiskDbContext> dbContextFactory,
    AssessRiskHandler assessRiskHandler) : IPersistentRiskAssessmentService
{
    public async Task<PersistedRiskAssessment> AssessAsync(
        PersistentRiskAssessmentCommand command,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(command);
        var fingerprint = RiskRequestFingerprint.Compute(command);

        await using var db = await dbContextFactory.CreateDbContextAsync(cancellationToken);
        var existing = await db.RiskAssessments
            .AsNoTracking()
            .SingleOrDefaultAsync(item => item.TransactionId == command.TransactionId, cancellationToken);
        if (existing is not null)
        {
            return ReplayOrThrow(existing, fingerprint);
        }

        var result = assessRiskHandler.Handle(command.ToDomainCommand());
        var entity = ToEntity(command, fingerprint, result.Assessment);
        db.RiskAssessments.Add(entity);

        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return ToResult(entity);
        }
        catch (DbUpdateException exception) when (IsUniqueViolation(exception))
        {
            var raced = await db.RiskAssessments
                .AsNoTracking()
                .SingleOrDefaultAsync(item => item.TransactionId == command.TransactionId, cancellationToken);
            if (raced is null)
            {
                throw;
            }

            return ReplayOrThrow(raced, fingerprint);
        }
    }

    private static PersistedRiskAssessment ReplayOrThrow(RiskAssessmentEntity entity, string fingerprint)
    {
        if (!string.Equals(entity.RequestFingerprint, fingerprint, StringComparison.Ordinal))
        {
            throw new RiskAssessmentConflictException(entity.TransactionId);
        }

        return ToResult(entity);
    }

    private static RiskAssessmentEntity ToEntity(
        PersistentRiskAssessmentCommand command,
        string fingerprint,
        RiskAssessment assessment)
    {
        var reasons = assessment.Reasons
            .Select(reason => new PersistedReason(reason.Code, reason.Points))
            .ToArray();
        return new RiskAssessmentEntity
        {
            Id = Guid.NewGuid(),
            TransactionId = command.TransactionId,
            SourceAccountId = command.SourceAccountId,
            DestinationAccountId = command.DestinationAccountId,
            AmountCents = command.AmountCents,
            OperationType = command.OperationType,
            RequestFingerprint = fingerprint,
            Decision = assessment.Decision.ToString(),
            RiskScore = assessment.RiskScore,
            ReasonsJson = JsonSerializer.Serialize(reasons),
            RulesVersion = assessment.RulesVersion,
            CreatedAt = DateTimeOffset.UtcNow,
        };
    }

    private static PersistedRiskAssessment ToResult(RiskAssessmentEntity entity)
    {
        var decision = Enum.Parse<RiskDecision>(entity.Decision, ignoreCase: false);
        var reasons = JsonSerializer.Deserialize<PersistedReason[]>(entity.ReasonsJson) ?? [];
        var assessment = new RiskAssessment(
            entity.TransactionId,
            decision,
            RiskScore.FromPoints(entity.RiskScore),
            reasons.Select(reason => new RiskReason(reason.Code, reason.Points)).ToArray(),
            entity.RulesVersion);
        return new PersistedRiskAssessment(entity.Id, assessment);
    }

    private static bool IsUniqueViolation(DbUpdateException exception) =>
        exception.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation };

    private sealed record PersistedReason(string Code, int Points);
}
