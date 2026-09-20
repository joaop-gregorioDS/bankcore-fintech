using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BankCore.Risk.IntegrationTests;

public sealed class RiskPersistencePostgresTests
{
    private static readonly Guid TransactionId = Guid.Parse("11111111-1111-1111-1111-111111111111");
    private static readonly Guid SourceAccountId = Guid.Parse("22222222-2222-2222-2222-222222222222");
    private static readonly Guid DestinationAccountId = Guid.Parse("33333333-3333-3333-3333-333333333333");

    [Fact]
    public async Task Migration_is_applied_and_schema_is_versioned()
    {
        await ClearAsync();
        var factory = CreateFactory();
        await using var db = await factory.CreateDbContextAsync();

        Assert.Empty(await db.Database.GetPendingMigrationsAsync());
        var appliedMigrations = await db.Database.GetAppliedMigrationsAsync();
        Assert.Single(appliedMigrations);
        Assert.EndsWith("_InitialRiskSchema", appliedMigrations.Single(), StringComparison.Ordinal);
        Assert.True(await db.Database.CanConnectAsync());
        Assert.False(await db.RiskAssessments.AnyAsync());
    }

    [Fact]
    public async Task Replay_after_service_restart_returns_same_persisted_assessment()
    {
        await ClearAsync();
        var command = CreateCommand();
        var first = await AssessAsync(command);

        var replay = await AssessAsync(command);

        Assert.Equal(first.AssessmentId, replay.AssessmentId);
        Assert.Equal(first.Assessment.Decision, replay.Assessment.Decision);
        Assert.Equal(first.Assessment.RiskScore, replay.Assessment.RiskScore);
    }

    [Fact]
    public async Task Different_fingerprint_returns_conflict_without_second_row()
    {
        await ClearAsync();
        var command = CreateCommand();
        _ = await AssessAsync(command);

        await Assert.ThrowsAsync<RiskAssessmentConflictException>(() =>
            AssessAsync(CreateCommand(500_000)));

        var factory = CreateFactory();
        await using var db = await factory.CreateDbContextAsync();
        Assert.Single(await db.RiskAssessments.Where(item => item.TransactionId == command.TransactionId).ToListAsync());
    }

    [Fact]
    public async Task Concurrent_requests_create_exactly_one_financial_assessment()
    {
        await ClearAsync();
        var command = CreateCommand();
        var results = await Task.WhenAll(
            Enumerable.Range(0, 20).Select(_ => AssessAsync(command)));

        Assert.Single(results.Select(result => result.AssessmentId).Distinct());

        var factory = CreateFactory();
        await using var db = await factory.CreateDbContextAsync();
        Assert.Single(await db.RiskAssessments.Where(item => item.TransactionId == command.TransactionId).ToListAsync());
        Assert.Single(await db.RiskAssessments.ToListAsync());
        Assert.DoesNotContain(results, result => result.AssessmentId == Guid.Empty);
    }

    private static PersistentRiskAssessmentCommand CreateCommand(long amountCents = 250_000) =>
        new(TransactionId, SourceAccountId, DestinationAccountId, amountCents, "pix");

    private static async Task<PersistedRiskAssessment> AssessAsync(PersistentRiskAssessmentCommand command)
    {
        var factory = CreateFactory();
        var service = new EfRiskAssessmentService(factory, new AssessRiskHandler());
        return await service.AssessAsync(command);
    }

    private static async Task ClearAsync()
    {
        var factory = CreateFactory();
        await using var db = await factory.CreateDbContextAsync();
        await db.RiskAssessments.ExecuteDeleteAsync();
    }

    private static IDbContextFactory<RiskDbContext> CreateFactory()
    {
        var connectionString = Environment.GetEnvironmentVariable("RISK_TEST_DATABASE_CONNECTION")
            ?? throw new InvalidOperationException("RISK_TEST_DATABASE_CONNECTION is required.");
        var options = new DbContextOptionsBuilder<RiskDbContext>()
            .UseNpgsql(connectionString)
            .Options;
        return new TestDbContextFactory(options);
    }

    private sealed class TestDbContextFactory(DbContextOptions<RiskDbContext> options) : IDbContextFactory<RiskDbContext>
    {
        public RiskDbContext CreateDbContext() => new(options);
    }
}
