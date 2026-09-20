using System.Data.Common;
using Microsoft.EntityFrameworkCore;

namespace BankCore.Risk.Infrastructure.Persistence;

public sealed class RiskDatabaseReadiness(IDbContextFactory<RiskDbContext> dbContextFactory)
{
    public async Task<bool> IsReadyAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var db = await dbContextFactory.CreateDbContextAsync(cancellationToken);
            await db.Database.ExecuteSqlRawAsync(
                "SELECT 1 FROM risk_assessments LIMIT 0",
                cancellationToken);
            return true;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception exception) when (exception is DbException or InvalidOperationException)
        {
            return false;
        }
    }
}
