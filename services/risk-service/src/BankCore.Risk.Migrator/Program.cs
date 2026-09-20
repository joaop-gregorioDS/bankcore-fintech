using BankCore.Risk.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;

var connectionString = Environment.GetEnvironmentVariable("RISK_DATABASE_CONNECTION")
    ?? throw new InvalidOperationException("RISK_DATABASE_CONNECTION is required.");

var options = new DbContextOptionsBuilder<RiskDbContext>()
    .UseNpgsql(connectionString, npgsql => npgsql.MigrationsAssembly(typeof(RiskDbContext).Assembly.FullName))
    .Options;

await using var db = new RiskDbContext(options);
await db.Database.MigrateAsync();
Console.WriteLine("Risk database migrations applied.");
