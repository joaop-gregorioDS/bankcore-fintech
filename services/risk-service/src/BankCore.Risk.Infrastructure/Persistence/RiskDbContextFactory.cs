using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace BankCore.Risk.Infrastructure.Persistence;

public sealed class RiskDbContextFactory : IDesignTimeDbContextFactory<RiskDbContext>
{
    public RiskDbContext CreateDbContext(string[] args)
    {
        var connectionString = Environment.GetEnvironmentVariable("RISK_DATABASE_CONNECTION")
            ?? "Host=localhost;Port=5432;Database=bankcore_risk;Username=bankadmin;Password=design-time-only";
        var options = new DbContextOptionsBuilder<RiskDbContext>()
            .UseNpgsql(connectionString, npgsql => npgsql.MigrationsAssembly(typeof(RiskDbContext).Assembly.FullName))
            .Options;
        return new RiskDbContext(options);
    }
}
